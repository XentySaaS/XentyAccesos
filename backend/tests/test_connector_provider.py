"""F-D — ConnectorProvider: cliente REST del XCC tras la interfaz, con failover real por el Router.

Verifica la firma HMAC (misma cadena que valida el XCC), la degradación sin config, el registro del
proveedor y el **failover xcc→sandbox** cuando el Connector no responde. No requiere el XCC vivo: la
red se simula (monkeypatch de ``requests.post``).
"""

import pytest
from django.core.cache import cache
from django_tenants.utils import schema_context

from apps.mensajeria import router
from apps.mensajeria.connector_provider import ConnectorProvider, _firmar

pytestmark = pytest.mark.django_db


class _FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def _config_connector(**kwargs):
    from apps.tenants.models import ConfiguracionConnector

    defaults = {"habilitado": True, "url_base": "http://xcc.test", "hmac_secret": "secreto-xcc"}
    defaults.update(kwargs)
    ConfiguracionConnector.objects.all().delete()
    return ConfiguracionConnector.objects.create(**defaults)


def test_registro_incluye_xcc():
    from apps.mensajeria.proveedores import registro_proveedores

    assert "xcc" in registro_proveedores()


def test_connector_sin_config_devuelve_error(dos_tenants):
    """Sin ConfiguracionConnector habilitada, el proveedor degrada (ok=False) sin tocar la red."""
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        res = ConnectorProvider().enviar("5218112223344", "hola")
    assert res.ok is False and res.error == "xcc-no-configurado"


def test_connector_firma_y_postea(dos_tenants, monkeypatch):
    """El proveedor firma con el esquema del XCC y reporta ok con el message_id en 202."""
    t1, _ = dos_tenants
    _config_connector()

    capturado = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        capturado.update(url=url, data=data, headers=headers, timeout=timeout)
        return _FakeResp(202, {"message_id": "xcc-123"})

    monkeypatch.setattr("requests.post", fake_post)

    with schema_context(t1.schema_name):
        res = ConnectorProvider().enviar("5218112223344", "hola")

    assert res.ok is True and res.proveedor == "xcc" and res.external_id == "xcc-123"
    assert capturado["url"] == "http://xcc.test/v1/messages"
    h = capturado["headers"]
    assert h["X-XCC-Tenant"] == t1.schema_name
    # La firma enviada coincide con la recomputada sobre los MISMOS bytes → interop con el XCC.
    esperada = _firmar(
        "secreto-xcc",
        "POST",
        "/v1/messages",
        t1.schema_name,
        h["X-XCC-Timestamp"],
        h["X-XCC-Nonce"],
        capturado["data"],
    )
    assert h["X-XCC-Signature"] == esperada


def test_connector_media_b64(dos_tenants, monkeypatch):
    """Un adjunto (bytes) se manda como base64 con type=image/document (sin URL pública)."""
    import json

    from apps.mensajeria.proveedores import AdjuntoWhatsApp

    t1, _ = dos_tenants
    _config_connector()
    capt = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        capt["data"] = data
        return _FakeResp(202, {"message_id": "m1"})

    monkeypatch.setattr("requests.post", fake_post)
    adj = AdjuntoWhatsApp(
        nombre_archivo="gafete.png",
        contenido=b"\x89PNG\r\n",
        mimetype="image/png",
        caption="ignorado",
    )
    with schema_context(t1.schema_name):
        res = ConnectorProvider().enviar("5218112223344", "cuerpo del mensaje", adjunto=adj)

    assert res.ok is True
    body = json.loads(capt["data"])
    assert body["type"] == "image"
    assert body["media_b64"] and body["filename"] == "gafete.png"
    assert body["mimetype"] == "image/png"
    assert body["caption"] == "cuerpo del mensaje"  # el caption lo pone el cuerpo, no el adjunto
    assert "text" not in body and "media_url" not in body


def test_connector_http_no_202_es_fallo(dos_tenants, monkeypatch):
    t1, _ = dos_tenants
    _config_connector()
    monkeypatch.setattr("requests.post", lambda *a, **k: _FakeResp(500))
    with schema_context(t1.schema_name):
        res = ConnectorProvider().enviar("5218112223344", "hola")
    assert res.ok is False and res.error == "xcc-http-500"


def test_router_usa_connection_id_del_tenant(dos_tenants):
    """El Router instancia el xcc con el connection_id (número) que eligió el tenant."""
    from apps.mensajeria.models import PreferenciaMensajeria

    t1, _ = dos_tenants
    _config_connector()
    cache.clear()  # snapshot de config fresco (xcc ON)
    with schema_context(t1.schema_name):
        pref = PreferenciaMensajeria.cargar()
        pref.proveedores_orden = ["xcc"]
        pref.connection_id = "ventas"
        pref.save()
        provs = router.proveedores_para(t1.schema_name, pref=pref)
    xcc = [p for p in provs if p.nombre == "xcc"]
    assert xcc, "el xcc debe estar en los proveedores (master switch ON)"
    assert xcc[0].connection_id == "ventas"


def test_preferencia_serializer_rechaza_connection_id_invalido():
    from apps.mensajeria.preferencia_api import PreferenciaMensajeriaSerializer

    s = PreferenciaMensajeriaSerializer(data={"connection_id": "mal/valor"}, partial=True)
    assert not s.is_valid()
    assert "connection_id" in s.errors


def test_failover_xcc_a_sandbox_cuando_el_connector_cae(dos_tenants, monkeypatch):
    """E2E del Router: xcc primero; si el Connector no responde, failover a sandbox (nunca se pierde)."""
    from apps.mensajeria.breaker import CircuitBreaker
    from apps.mensajeria.models import PreferenciaMensajeria

    t1, _ = dos_tenants
    _config_connector()
    cache.clear()  # el Router cachea el snapshot de config; forzar lectura fresca (xcc ON)

    def boom(*a, **k):
        raise ConnectionError("connector caído")

    monkeypatch.setattr("requests.post", boom)

    with schema_context(t1.schema_name):
        CircuitBreaker("xcc").registrar_exito()  # breaker limpio
        pref = PreferenciaMensajeria.cargar()
        pref.proveedores_orden = ["xcc", "sandbox"]
        pref.save()
        res = router.enviar("5218112223344", "hola", registrar=False)
        CircuitBreaker("xcc").registrar_exito()  # no contaminar otros tests

    assert res.ok is True and res.proveedor == "sandbox"  # failover exitoso
