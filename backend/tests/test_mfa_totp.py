"""MFA por TOTP: desactivación (borra el secreto y ajusta mfa_habilitado)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def _usuario(email="totp@e.mx"):
    from apps.accounts.models import Usuario

    u = Usuario.objects.create_user(email=email, nombre="TOTP", password="Secreta123!")
    u.mfa_totp_secret = "JBSWY3DPEHPK3PXP"
    u.mfa_habilitado = True
    u.save(update_fields=["mfa_totp_secret", "mfa_habilitado"])
    return u


def test_desactivar_borra_secreto_y_apaga_mfa_sin_webauthn(dos_tenants):
    from common.mfa_api import DesactivarTOTPView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario()
        resp = DesactivarTOTPView().post(SimpleNamespace(user=u, auth={}))
        assert resp.status_code == 200
        u.refresh_from_db()
        assert not u.mfa_totp_secret
        # Sin llaves WebAuthn, el MFA queda deshabilitado por completo.
        assert u.mfa_habilitado is False


def test_desactivar_conserva_mfa_si_hay_webauthn(dos_tenants):
    from webauthn.helpers import bytes_to_base64url

    from apps.accounts.models import CredencialWebAuthn
    from common.mfa_api import DesactivarTOTPView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(email="mixto@e.mx")
        CredencialWebAuthn.objects.create(
            usuario=u, credential_id=bytes_to_base64url(b"c1"), public_key="pk"
        )
        DesactivarTOTPView().post(SimpleNamespace(user=u, auth={}))
        u.refresh_from_db()
        assert not u.mfa_totp_secret
        # Conserva una llave WebAuthn → el MFA sigue activo por esa vía.
        assert u.mfa_habilitado is True
