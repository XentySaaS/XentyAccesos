"""MFA obligatorio del super-admin del control plane (feat 2026-07-08).

Cubre la lógica propia de la feature de auto-siembra + 2FA estricto, no la criptografía de pyotp:
  - ``bootstrap_superadmin``: idempotencia, MFA obligatorio, siembra env-driven.
  - ``SuperAdminLoginView``: banderas ``mfa_pendiente`` / ``mfa_enrolar`` y claim ``mfa=pending``.
  - ``ActivarTOTPView``: en sesión pendiente la activación emite tokens ``full`` (un solo código).

El super-admin vive en ``public`` (SHARED_APPS) y es singleton, así que no hace falta tenant: cada
test crea el suyo y la transacción de ``django_db`` lo revierte.
"""

import pyotp
import pytest
from django.core.management import call_command
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import AccessToken

from apps.tenants.admin_api import SuperAdminLoginView
from apps.tenants.models import SuperAdmin
from common.mfa import generar_secreto
from common.mfa_api import ActivarTOTPView, EnrolarTOTPView

pytestmark = pytest.mark.django_db

_PWD = "Sup3rSecreta!"
_factory = APIRequestFactory()


def _crear_admin(email="admin@xenty.mx", *, mfa=True, totp=None):
    """Super-admin de prueba. ``mfa`` = obligatorio; ``totp`` = secreto ya enrolado (o None)."""
    return SuperAdmin.objects.create_user(
        email=email, nombre="Super", password=_PWD, mfa_habilitado=mfa, mfa_totp_secret=totp
    )


def _login(email, password, ip="198.51.100.1"):
    # IP única por llamada para no compartir el bucket de rate-limit (10/m/IP) entre tests.
    req = _factory.post("/api/admin/login/", {"email": email, "password": password}, format="json")
    req.META["REMOTE_ADDR"] = ip
    return SuperAdminLoginView.as_view()(req)


def _token(pendiente):
    return {"ctx": "superadmin", "mfa": "pending" if pendiente else "ok"}


def _enrolar(admin, *, pendiente=True):
    """Genera el QR (cachea el secreto en curso) y devuelve el secreto, como haría el SPA."""
    req = _factory.post("/api/admin/mfa/totp/enrolar/")
    force_authenticate(req, user=admin, token=_token(pendiente))
    return EnrolarTOTPView.as_view()(req).data["secret"]


def _activar(admin, codigo, *, pendiente=True):
    req = _factory.post("/api/admin/mfa/totp/activar/", {"codigo": codigo}, format="json")
    force_authenticate(req, user=admin, token=_token(pendiente))
    return ActivarTOTPView.as_view()(req)


# ── bootstrap_superadmin ─────────────────────────────────────────────────────
def test_bootstrap_crea_superadmin_con_mfa_obligatorio(settings):
    settings.SUPERADMIN_EMAIL = "Boot@Xenty.MX"
    settings.SUPERADMIN_PASSWORD = _PWD
    settings.SUPERADMIN_NOMBRE = "Root"

    call_command("bootstrap_superadmin")

    admin = SuperAdmin.objects.get()
    assert admin.email == "boot@xenty.mx", "El email debe normalizarse (lower + strip)"
    assert admin.nombre == "Root"
    assert admin.mfa_habilitado is True, "MFA debe quedar obligatorio desde la siembra"
    assert not admin.mfa_totp_secret, "Sin factor enrolado: se enrola en el primer login"
    assert admin.check_password(_PWD)


def test_bootstrap_es_idempotente(settings):
    existente = _crear_admin(email="ya@xenty.mx")
    settings.SUPERADMIN_EMAIL = "otro@xenty.mx"
    settings.SUPERADMIN_PASSWORD = _PWD

    call_command("bootstrap_superadmin")  # no debe crear un segundo ni violar el singleton

    assert SuperAdmin.objects.count() == 1
    assert SuperAdmin.objects.get().pk == existente.pk


def test_bootstrap_sin_credenciales_no_siembra(settings):
    settings.SUPERADMIN_EMAIL = ""
    settings.SUPERADMIN_PASSWORD = ""

    call_command("bootstrap_superadmin")

    assert not SuperAdmin.objects.exists()


# ── SuperAdminLoginView ──────────────────────────────────────────────────────
def test_login_sin_factor_pide_enrolar():
    _crear_admin()
    resp = _login("admin@xenty.mx", _PWD)

    assert resp.status_code == 200
    assert resp.data["mfa_pendiente"] is True
    assert resp.data["mfa_enrolar"] is True, "Sin TOTP ni passkey: el SPA debe mostrar el QR"
    assert AccessToken(resp.data["access"])["mfa"] == "pending"


def test_login_con_totp_enrolado_no_pide_enrolar():
    _crear_admin(totp=generar_secreto())
    resp = _login("admin@xenty.mx", _PWD)

    assert resp.status_code == 200
    assert resp.data["mfa_pendiente"] is True, "Sigue pendiente hasta verificar el 2º factor"
    assert resp.data["mfa_enrolar"] is False, "Ya hay factor: solo verificar, no enrolar"


def test_login_con_passkey_enrolada_no_pide_enrolar():
    from apps.tenants.models import CredencialWebAuthnAdmin

    admin = _crear_admin()
    CredencialWebAuthnAdmin.objects.create(
        superadmin=admin, credential_id="cred-abc", public_key="pk"
    )
    resp = _login("admin@xenty.mx", _PWD)

    assert resp.data["mfa_pendiente"] is True
    assert resp.data["mfa_enrolar"] is False, "Passkey cuenta como factor enrolado"


def test_login_password_incorrecta_401():
    _crear_admin()
    resp = _login("admin@xenty.mx", "incorrecta")

    assert resp.status_code == 401
    assert "access" not in resp.data


def test_login_email_inexistente_401():
    resp = _login("nadie@xenty.mx", _PWD)

    assert resp.status_code == 401


# ── ActivarTOTPView (enrolamiento en sesión pendiente) ───────────────────────
def test_activar_en_sesion_pendiente_emite_tokens_full():
    admin = _crear_admin()  # sin secreto persistido
    secreto = _enrolar(admin, pendiente=True)  # cachea el secreto en curso
    codigo = pyotp.TOTP(secreto).now()

    resp = _activar(admin, codigo, pendiente=True)

    assert resp.status_code == 200
    assert "access" in resp.data and "refresh" in resp.data, "Enrolamiento en un solo código"
    assert AccessToken(resp.data["access"])["mfa"] == "ok"
    admin.refresh_from_db()
    assert admin.mfa_habilitado is True
    assert bool(admin.mfa_totp_secret) is True, "El secreto se persiste recién al activar"


def test_activar_sesion_completa_no_reemite_tokens():
    admin = _crear_admin()
    secreto = _enrolar(admin, pendiente=False)
    codigo = pyotp.TOTP(secreto).now()

    resp = _activar(admin, codigo, pendiente=False)

    assert resp.status_code == 200
    assert resp.data == {"detail": "MFA activado."}, "Sesión ya completa: no reemite tokens"


def test_activar_codigo_invalido_400():
    admin = _crear_admin()
    _enrolar(admin, pendiente=True)  # hay enrolamiento en curso, pero el código no corresponde

    resp = _activar(admin, "000000", pendiente=True)

    assert resp.status_code == 400
    assert "access" not in resp.data


def test_activar_sin_enrolamiento_en_curso_400():
    # No se generó el QR (o expiró): sin secreto en cache, activar no puede confirmar.
    admin = _crear_admin(totp=None)

    resp = _activar(admin, "123456", pendiente=True)

    assert resp.status_code == 400
    admin.refresh_from_db()
    assert not admin.mfa_totp_secret
