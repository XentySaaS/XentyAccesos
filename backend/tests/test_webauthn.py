"""WebAuthn (2º factor): generación de opciones, reto en cache, registry por ctx y aislamiento.

La verificación criptográfica de attestation/assertion la hace py_webauthn (no se reimplementa aquí);
estos tests cubren la lógica propia: opciones bien formadas, reto cacheado, credenciales por schema.
"""

import pytest
from django.core.cache import cache
from django_tenants.utils import schema_context
from webauthn.helpers import bytes_to_base64url

from common import webauthn

pytestmark = pytest.mark.django_db


def _usuario(email="mfa@e.mx"):
    from apps.accounts.models import Usuario

    return Usuario.objects.create_user(email=email, nombre="MFA User", password="Secreta123!")


def test_cred_model_registry():
    assert webauthn.cred_model("acceso") is not None
    assert webauthn.cred_model("superadmin") is not None
    assert webauthn.cred_model("proveedores") is None  # no soportado en este slice


def test_opciones_registro_genera_reto_y_cachea(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        data = webauthn.opciones_registro(u, "acceso", t1.schema_name)
        assert data["rp"]["id"] == "localhost"
        assert "challenge" in data and data["challenge"]
        assert data["user"]["name"] == "mfa@e.mx"
        # El reto quedó en cache para la verificación posterior.
        assert cache.get(f"webauthn:reg:acceso:{t1.schema_name}:{u.pk}")


def test_opciones_login_incluye_credenciales_del_usuario(dos_tenants):
    from apps.accounts.models import CredencialWebAuthn

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        cid = bytes_to_base64url(b"cred-1")
        CredencialWebAuthn.objects.create(usuario=u, credential_id=cid, public_key="pk")
        data = webauthn.opciones_login(u, "acceso", t1.schema_name)
        ids = [c["id"] for c in data.get("allowCredentials", [])]
        assert cid in ids


def test_registrar_sin_reto_falla(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        cache.delete(f"webauthn:reg:acceso:{t1.schema_name}:{u.pk}")
        ok, error = webauthn.registrar(u, "acceso", t1.schema_name, {"id": "x"}, "Llave")
        assert ok is False and "expiró" in error


def test_verificar_login_sin_reto_falla(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        ok, error = webauthn.verificar_login(u, "acceso", t1.schema_name, {"id": "x"})
        assert ok is False and "expiró" in error


def test_aislamiento_credenciales_webauthn_por_tenant(dos_tenants):
    from apps.accounts.models import CredencialWebAuthn

    t1, t2 = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(email="t1@e.mx")
        CredencialWebAuthn.objects.create(
            usuario=u, credential_id=bytes_to_base64url(b"c1"), public_key="pk"
        )
        assert CredencialWebAuthn.objects.count() == 1
    with schema_context(t2.schema_name):
        assert (
            CredencialWebAuthn.objects.count() == 0
        ), "Fuga: credencial del tenant 1 vista en el 2"
