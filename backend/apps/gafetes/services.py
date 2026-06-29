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


# ── Gafete compuesto (puerto del GenerateBadge del origen, con Pillow) ──────────

_INK = (15, 27, 45)        # --ink-900
_BLANCO = (255, 255, 255)
_GRIS = (203, 213, 225)    # --slate-300

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
]


def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidatos = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]
        if bold else _FONT_PATHS
    )
    for ruta in candidatos:
        try:
            return ImageFont.truetype(ruta, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _texto_centrado(draw, y: int, texto: str, font, color, ancho: int) -> int:
    """Dibuja texto centrado horizontalmente; devuelve la Y siguiente."""
    if not texto:
        return y
    bbox = draw.textbbox((0, 0), texto, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((ancho - w) / 2, y), texto, font=font, fill=color)
    return y + h + 14


def componer_gafete(
    *,
    token: str,
    titulo: str,
    recinto: str,
    lineas: list[str],
    foto_bytes: bytes | None = None,
    empresa: str = "XENTY ACCESO",
) -> bytes:
    """Compone el gafete (tarjeta oscura + foto circular + datos + QR) y devuelve PNG.

    El QR lleva el ``token`` cifrado de :func:`emitir_qr` (inviolable). Equivalente al
    ``generateEventBadge`` / ``generateParkingBadge`` del origen, pero con QR Fernet.
    """
    from io import BytesIO

    from PIL import Image, ImageDraw

    ancho, alto, radio = 600, 950, 36
    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, ancho, alto], radius=radio, fill=_INK)

    # Encabezado: marca
    y = _texto_centrado(draw, 40, empresa, _font(26, bold=True), _GRIS, ancho)

    # Foto circular (opcional)
    if foto_bytes:
        try:
            foto = Image.open(BytesIO(foto_bytes)).convert("RGBA")
            lado = min(foto.size)
            foto = foto.crop((
                (foto.width - lado) // 2, (foto.height - lado) // 2,
                (foto.width + lado) // 2, (foto.height + lado) // 2,
            )).resize((180, 180))
            mascara = Image.new("L", (180, 180), 0)
            ImageDraw.Draw(mascara).ellipse([0, 0, 180, 180], fill=255)
            cx = (ancho - 180) // 2
            img.paste(foto, (cx, y + 6), mascara)
            y += 180 + 24
        except Exception:  # noqa: BLE001 — foto opcional/ilegible
            y += 10

    # Título (nombre de la persona o del evento)
    y = _texto_centrado(draw, y, titulo, _font(34, bold=True), _BLANCO, ancho)

    # Pill del recinto
    if recinto:
        f = _font(22, bold=True)
        bbox = draw.textbbox((0, 0), recinto, font=f)
        w = bbox[2] - bbox[0]
        bx0, bx1 = (ancho - w) / 2 - 18, (ancho + w) / 2 + 18
        draw.rounded_rectangle([bx0, y, bx1, y + 44], radius=22, fill=(37, 99, 235))
        draw.text(((ancho - w) / 2, y + 9), recinto, font=f, fill=_BLANCO)
        y += 44 + 22

    # Líneas de datos
    f_linea = _font(22)
    for linea in lineas:
        y = _texto_centrado(draw, y, linea, f_linea, _BLANCO, ancho)

    # QR (token cifrado)
    qr = qrcode.make(token).convert("RGBA").resize((260, 260))
    qx = (ancho - 260) // 2
    qy = max(y + 10, alto - 300)
    draw.rounded_rectangle([qx - 14, qy - 14, qx + 274, qy + 274], radius=18, fill=_BLANCO)
    img.paste(qr, (qx, qy))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
