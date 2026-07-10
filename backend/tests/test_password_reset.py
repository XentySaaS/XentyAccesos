"""Recuperación de contraseña self-service (acceso + proveedores).

Cubre la lógica propia del flujo (``common.password_reset``): token firmado tenant-aware, un solo
uso (huella de la contraseña), expiración, aislamiento cruzado entre tenants y contextos, y la
respuesta genérica de ``solicitar`` (sin enumeración de usuarios). Los modelos autenticatables viven
en el schema del tenant, así que las pruebas entran en ``schema_context`` sobre el fixture
``dos_tenants``.
"""

import itertools

import pytest
from django_tenants.utils import schema_context
from rest_framework.test import APIRequestFactory

from apps.accounts.api import AccesoConfirmarResetView, AccesoSolicitarResetView
from apps.accounts.models import Usuario
from apps.proveedores.api import ProveedorConfirmarResetView
from common.password_reset import generar_token_reset

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()
_ips = itertools.count(1)  # IP única por llamada: no compartir el bucket de rate-limit entre tests.


def _post(view, payload):
    req = _factory.post("/x/", payload, format="json")
    req.META["REMOTE_ADDR"] = f"203.0.113.{next(_ips) % 254 + 1}"
    return view.as_view()(req)


def _usuario(email="user@e.mx", password="ClaveVieja1!"):
    return Usuario.objects.create_user(email=email, nombre="User", password=password)


# ── Token + confirmación ─────────────────────────────────────────────────────
def test_confirmar_cambia_la_contrasena(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        token = generar_token_reset(u, "acceso")

        resp = _post(AccesoConfirmarResetView, {"token": token, "password": "ClaveNueva9!"})

        assert resp.status_code == 200
        u.refresh_from_db()
        assert u.check_password("ClaveNueva9!")
        assert not u.check_password("ClaveVieja1!")


def test_token_es_de_un_solo_uso(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        token = generar_token_reset(u, "acceso")
        assert _post(AccesoConfirmarResetView, {"token": token, "password": "ClaveNueva9!"}).status_code == 200

        # El mismo token ya no sirve: la huella de la contraseña cambió.
        resp = _post(AccesoConfirmarResetView, {"token": token, "password": "Otra12345!"})
        assert resp.status_code == 400
        u.refresh_from_db()
        assert u.check_password("ClaveNueva9!"), "La 2ª petición no debe cambiar la contraseña"


def test_token_expirado_se_rechaza(dos_tenants, monkeypatch):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        token = generar_token_reset(u, "acceso")
        monkeypatch.setattr("common.password_reset.MAX_AGE", -1)  # todo token cuenta como vencido

        resp = _post(AccesoConfirmarResetView, {"token": token, "password": "ClaveNueva9!"})
        assert resp.status_code == 400
        u.refresh_from_db()
        assert u.check_password("ClaveVieja1!")


def test_token_invalido_se_rechaza(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        _usuario()
        resp = _post(AccesoConfirmarResetView, {"token": "basura.no.firmada", "password": "ClaveNueva9!"})
        assert resp.status_code == 400


def test_token_de_otro_tenant_se_rechaza(dos_tenants):
    t1, t2 = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        token = generar_token_reset(u, "acceso")  # emitido para el schema de t1
    with schema_context(t2.schema_name):
        # Confirmar en t2: el claim tenant del token no coincide con el schema de la petición.
        resp = _post(AccesoConfirmarResetView, {"token": token, "password": "ClaveNueva9!"})
        assert resp.status_code == 400


def test_token_de_otro_contexto_se_rechaza(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        token = generar_token_reset(u, "acceso")  # contexto acceso
        # Confirmarlo con la vista de proveedores (ctx="proveedores") debe fallar.
        resp = _post(ProveedorConfirmarResetView, {"token": token, "password": "ClaveNueva9!"})
        assert resp.status_code == 400


def test_password_corta_se_rechaza(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        token = generar_token_reset(u, "acceso")
        resp = _post(AccesoConfirmarResetView, {"token": token, "password": "corta"})
        assert resp.status_code == 400
        u.refresh_from_db()
        assert u.check_password("ClaveVieja1!")


# ── Solicitud (sin enumeración) ──────────────────────────────────────────────
def test_solicitar_correo_existente_envia_email(dos_tenants, mailoutbox):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        _usuario(email="existe@e.mx")
        resp = _post(AccesoSolicitarResetView, {"email": "existe@e.mx"})

    assert resp.status_code == 200
    assert "instrucciones" in resp.data["detail"].lower()
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["existe@e.mx"]
    assert mailoutbox[0].alternatives, "El correo debe llevar la plantilla HTML de marca"


def test_solicitar_correo_inexistente_no_filtra(dos_tenants, mailoutbox):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        resp = _post(AccesoSolicitarResetView, {"email": "nadie@e.mx"})

    # Misma respuesta que un correo válido, pero sin enviar nada.
    assert resp.status_code == 200
    assert "instrucciones" in resp.data["detail"].lower()
    assert len(mailoutbox) == 0


def test_solicitar_usuario_inactivo_no_envia(dos_tenants, mailoutbox):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(email="baja@e.mx")
        u.activo = False
        u.save(update_fields=["activo"])
        resp = _post(AccesoSolicitarResetView, {"email": "baja@e.mx"})

    assert resp.status_code == 200
    assert len(mailoutbox) == 0
