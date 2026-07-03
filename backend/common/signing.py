"""Tokens de invitación firmados (REMEDIACION §C3/§7.3).

Reemplazan el esquema ``sha1(clave.exp)`` / AES-ECB del origen por ``django.core.signing`` (firma
HMAC con ``SECRET_KEY`` + timestamp). Verificable sin estado y con expiración (72h por defecto).
"""

from __future__ import annotations

from django.core import signing

_SALT = "invitacion-proveedor"
VIGENCIA_HORAS = 72


def firmar_invitacion(proveedor_id: int, tenant: str) -> str:
    """Token firmado para invitar a una empresa a completar su onboarding."""
    return signing.dumps({"proveedor_id": proveedor_id, "tenant": tenant}, salt=_SALT)


def leer_invitacion(token: str, max_age_horas: int = VIGENCIA_HORAS) -> dict:
    """Devuelve el payload si la firma es válida y no expiró. Lanza ``signing.BadSignature``/``SignatureExpired``."""
    return signing.loads(token, salt=_SALT, max_age=max_age_horas * 3600)
