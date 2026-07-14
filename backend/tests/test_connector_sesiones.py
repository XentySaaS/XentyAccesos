"""Proxy firmado de sesiones del XCC: el backend firma por las SPAs (nunca exponen el secreto HMAC).

Cubre el cliente (`connector_client`) —degradación sin config y firma correcta— y la vista del
super-admin (`AdminSesionView`) —estado por tenant y validación de parámetros—. La red al XCC se
simula (monkeypatch de `requests.request`).
"""

import pytest
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIRequestFactory, force_authenticate

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload

    def json(self):
        return self._p


def _set_config(**kw):
    from apps.tenants.models import ConfiguracionConnector

    defaults = {"habilitado": True, "url_base": "http://xcc.test", "hmac_secret": "sec"}
    defaults.update(kw)
    with schema_context(get_public_schema_name()):
        ConfiguracionConnector.objects.all().delete()
        ConfiguracionConnector.objects.create(**defaults)


def _clear_config():
    from apps.tenants.models import ConfiguracionConnector

    with schema_context(get_public_schema_name()):
        ConfiguracionConnector.objects.all().delete()


def _su_request(method, url, **params):
    from apps.tenants.models import SuperAdmin

    su, _ = SuperAdmin.objects.get_or_create(email="su@xenty.mx", defaults={"nombre": "SU"})
    req = getattr(_factory, method)(url)
    force_authenticate(req, user=su, token={"ctx": "superadmin", "mfa": "ok"})
    return req


def test_client_sin_config_lanza():
    from apps.mensajeria.connector_client import ConnectorNoDisponible, solicitar

    _clear_config()
    with pytest.raises(ConnectorNoDisponible):
        solicitar("acme", "GET", "/v1/status")


def test_client_firma_y_devuelve(monkeypatch):
    from apps.mensajeria.connector_client import solicitar
    from apps.mensajeria.connector_provider import _firmar

    _set_config()
    cap = {}

    def fake(method, url, data=None, headers=None, timeout=None):
        cap.update(method=method, url=url, data=data, headers=headers)
        return _Resp(200, {"sessions": []})

    monkeypatch.setattr("requests.request", fake)
    r = solicitar("acme", "GET", "/v1/tenants/acme/sessions")

    assert r.status == 200 and r.data == {"sessions": []}
    assert cap["url"] == "http://xcc.test/v1/tenants/acme/sessions"
    h = cap["headers"]
    assert h["X-XCC-Tenant"] == "acme"
    # Firma recomputada sobre cuerpo vacío (GET) → interop con el XCC.
    esperada = _firmar(
        "sec",
        "GET",
        "/v1/tenants/acme/sessions",
        "acme",
        h["X-XCC-Timestamp"],
        h["X-XCC-Nonce"],
        b"",
    )
    assert h["X-XCC-Signature"] == esperada


def test_admin_sesion_estado(monkeypatch):
    from apps.tenants.connector_sesion_api import AdminSesionView

    _set_config()
    monkeypatch.setattr(
        "requests.request",
        lambda *a, **k: _Resp(
            200, {"sessions": [{"connection_id": "principal", "state": "open", "connected": True}]}
        ),
    )
    req = _su_request("get", "/x/?tenant=acme&connection_id=principal")
    resp = AdminSesionView.as_view()(req)

    assert resp.status_code == 200
    assert resp.data["tenant"] == "acme"
    assert resp.data["sessions"][0]["state"] == "open"


def test_admin_sesion_sin_config_503(monkeypatch):
    from apps.tenants.connector_sesion_api import AdminSesionView

    _clear_config()
    req = _su_request("get", "/x/?tenant=acme")
    resp = AdminSesionView.as_view()(req)
    assert resp.status_code == 503


def test_admin_sesion_falta_tenant():
    from apps.tenants.connector_sesion_api import AdminSesionView

    req = _su_request("get", "/x/")
    resp = AdminSesionView.as_view()(req)
    assert resp.status_code == 400
