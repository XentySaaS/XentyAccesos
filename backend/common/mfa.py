"""TOTP (segundo factor por app autenticadora) con pyotp.

Lógica pura sobre el secreto (base32); los modelos (Usuario/CuentaProveedor/SuperAdmin) guardan
``mfa_totp_secret`` cifrado (Fernet) y ``mfa_habilitado``. WebAuthn (passkeys) se añade aparte.
"""
from __future__ import annotations

import pyotp

ISSUER = "Xenty Acceso"


def generar_secreto() -> str:
    """Secreto TOTP base32 nuevo (para enrolar un dispositivo)."""
    return pyotp.random_base32()


def uri_aprovisionamiento(secret: str, email: str) -> str:
    """URI ``otpauth://`` para el QR que escanea la app autenticadora."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def verificar_totp(secret: str | None, codigo: str | None, *, valid_window: int = 1) -> bool:
    """Valida el código de 6 dígitos. ``valid_window=1`` tolera ±30s de desfase de reloj."""
    if not secret or not codigo:
        return False
    return pyotp.TOTP(secret).verify(str(codigo).strip(), valid_window=valid_window)
