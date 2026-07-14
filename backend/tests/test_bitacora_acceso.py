"""Bitácora de accesos al sistema (autenticación).

Verifica que el login (éxito y fallo) y el flujo de auth registran en ``config.BitacoraAcceso``
dentro del schema del tenant, capturando IP y dispositivo, y que el registro se **salta** en el
schema público (el super-admin del control plane no se audita aquí).
"""

from __future__ import annotations

import itertools

import pytest
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()
_ips = itertools.count(1)  # IP única por llamada: no compartir el bucket de rate-limit del login.

_UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML) Chrome/120 Safari/537.36"
)


def _login(payload):
    from apps.accounts.api import AccesoLoginView

    req = _factory.post("/x/", payload, format="json")
    req.META["REMOTE_ADDR"] = f"203.0.113.{next(_ips) % 254 + 1}"
    req.META["HTTP_USER_AGENT"] = _UA_CHROME
    return AccesoLoginView.as_view()(req)


def _usuario(email="op@e.mx", password="ClaveBuena1!"):
    from apps.accounts.models import Usuario

    return Usuario.objects.create_user(email=email, nombre="Operador", password=password)


def test_login_exitoso_registra_login(dos_tenants):
    from apps.config.models import BitacoraAcceso

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        _usuario()
        resp = _login({"email": "op@e.mx", "password": "ClaveBuena1!"})
        assert resp.status_code == 200

        reg = BitacoraAcceso.objects.get()
        assert reg.evento == BitacoraAcceso.Evento.LOGIN
        assert reg.contexto == BitacoraAcceso.Contexto.ACCESO
        assert reg.exito is True
        assert reg.actor_email == "op@e.mx"
        assert reg.usuario is not None
        assert reg.ip  # se capturó la IP del REMOTE_ADDR
        assert reg.dispositivo == "Chrome · Windows"


def test_login_password_incorrecta_registra_fallido(dos_tenants):
    from apps.config.models import BitacoraAcceso

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        _usuario()
        resp = _login({"email": "op@e.mx", "password": "malaClave9!"})
        assert resp.status_code == 401

        reg = BitacoraAcceso.objects.get()
        assert reg.evento == BitacoraAcceso.Evento.LOGIN_FALLIDO
        assert reg.exito is False
        assert reg.actor_email == "op@e.mx"
        assert reg.usuario is not None  # el correo existe, aunque la contraseña sea incorrecta
        assert "incorrecta" in reg.detalle.lower()


def test_login_correo_inexistente_registra_fallido(dos_tenants):
    from apps.config.models import BitacoraAcceso

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        resp = _login({"email": "nadie@e.mx", "password": "loquesea1!"})
        assert resp.status_code == 401

        reg = BitacoraAcceso.objects.get()
        assert reg.evento == BitacoraAcceso.Evento.LOGIN_FALLIDO
        assert reg.exito is False
        assert reg.actor_email == "nadie@e.mx"
        assert reg.usuario is None  # correo no registrado → sin FK


def test_login_cuenta_inactiva_registra_fallido(dos_tenants):
    from apps.config.models import BitacoraAcceso

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(email="baja@e.mx")
        u.activo = False
        u.save(update_fields=["activo"])
        resp = _login({"email": "baja@e.mx", "password": "ClaveBuena1!"})
        assert resp.status_code == 401

        reg = BitacoraAcceso.objects.get()
        assert reg.evento == BitacoraAcceso.Evento.LOGIN_FALLIDO
        assert "inactiva" in reg.detalle.lower()


def test_registrar_acceso_se_salta_en_public(dos_tenants):
    """El control plane (schema public) no se audita en la bitácora del tenant."""
    from apps.config.models import BitacoraAcceso
    from apps.config.services import registrar_acceso

    with schema_context(get_public_schema_name()):
        r = registrar_acceso(
            BitacoraAcceso.Evento.LOGIN, contexto="acceso", email="x@x.com", exito=True
        )
        assert r is None


def test_aislamiento_entre_tenants(dos_tenants):
    """El acceso registrado en t1 no aparece en el schema de t2."""
    from apps.config.models import BitacoraAcceso

    t1, t2 = dos_tenants
    with schema_context(t1.schema_name):
        _usuario()
        _login({"email": "op@e.mx", "password": "ClaveBuena1!"})
        assert BitacoraAcceso.objects.count() == 1
    with schema_context(t2.schema_name):
        assert BitacoraAcceso.objects.count() == 0
