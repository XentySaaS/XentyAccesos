"""Emisión y verificación de QR de acceso **inviolable** (REMEDIATION §C3).

Reemplaza el AES-128-ECB con clave fija en git del origen por un token **cifrado y autenticado con
Fernet** (AES-128-CBC + HMAC) que embebe ``id|contexto|tipo`` + ``jti`` único + ``exp`` (vigencia)
+ ``tenant``. Sin la ``SECRET_KEY_FERNET`` del servidor el QR no se puede forjar ni alterar.
"""
from __future__ import annotations

import json
import time
import uuid

import qrcode
from cryptography.fernet import InvalidToken

from common.crypto import get_fernet

# Códigos de contexto que van en el QR.
TIPO_EVENTO = "01"
TIPO_PARKING = "02"
TIPO_CITA = "03"


class QRInvalido(Exception):
    """QR ausente, alterado, expirado o de otro tenant."""


def emitir_qr(*, id: int, tipo: str, tenant: str, exp_epoch: float, contexto: str = "") -> str:
    """Emite un token QR firmado/cifrado con identificador único y vigencia."""
    payload = {
        "id": id, "tipo": tipo, "ctx": contexto or tipo,
        "jti": uuid.uuid4().hex, "exp": int(exp_epoch), "tenant": tenant,
    }
    return get_fernet().encrypt(json.dumps(payload).encode()).decode()


def verificar_qr(token: str, *, tenant: str | None = None) -> dict:
    """Descifra y valida el QR. Lanza ``QRInvalido`` si no es válido, expiró o es de otro tenant."""
    if not token:
        raise QRInvalido("QR ausente.")
    try:
        data = json.loads(get_fernet().decrypt(token.encode()).decode())
    except (InvalidToken, ValueError):
        raise QRInvalido("QR no válido (firma o formato).")
    if data.get("exp", 0) < time.time():
        raise QRInvalido("QR expirado.")
    if tenant is not None and data.get("tenant") != tenant:
        raise QRInvalido("QR de otro tenant.")
    return data


def generar_png(token: str) -> bytes:
    """Genera el PNG del gafete con el QR del token."""
    from io import BytesIO

    img = qrcode.make(token)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
