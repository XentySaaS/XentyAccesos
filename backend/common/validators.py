"""Validación de archivos subidos (REMEDIACION §A3): extensión + tamaño + MIME real.

El nombre lo asigna el servidor (nunca ``getClientOriginalName``). El MIME se valida con
python-magic cuando libmagic está disponible (sí en el contenedor); si no, degrada a
extensión+tamaño para no romper en entornos sin la librería nativa.
"""
from __future__ import annotations

import os
import re

from django.core.exceptions import ValidationError

# ── Validación de RFC (estructura + dígito verificador) ──────────────────────
_RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
_RFC_SEQ = "0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ"
_RFC_VAL = {c: i for i, c in enumerate(_RFC_SEQ)}
_RFC_VAL[" "] = 37
_RFC_VAL["Ñ"] = 38


def _digito_verificador_rfc(cuerpo: str) -> str:
    s = cuerpo.rjust(12, " ")
    suma = sum(_RFC_VAL[c] * (13 - i) for i, c in enumerate(s))
    dv = 11 - (suma % 11)
    return {11: "0", 10: "A"}.get(dv, str(dv))


def rfc_valido(rfc: str) -> bool:
    """Valida estructura y dígito verificador de un RFC (persona física o moral)."""
    rfc = (rfc or "").upper().strip()
    if not _RFC_RE.match(rfc):
        return False
    return _digito_verificador_rfc(rfc[:-1]) == rfc[-1]

# Firmas MIME aceptadas por extensión.
MIME_POR_EXT = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}


def validar_archivo(archivo, *, extensiones: tuple[str, ...], max_mb: int) -> None:
    """Valida un ``UploadedFile``. Lanza ``ValidationError`` si no cumple."""
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in extensiones:
        raise ValidationError(f"Extensión no permitida: {ext or '(sin extensión)'}.")

    if archivo.size > max_mb * 1024 * 1024:
        raise ValidationError(f"El archivo supera el máximo de {max_mb} MB.")

    cabecera = archivo.read(2048)
    archivo.seek(0)
    try:
        import magic  # python-magic; requiere libmagic nativo

        mime = magic.from_buffer(cabecera, mime=True)
    except Exception:
        return  # sin libmagic: extensión + tamaño ya validados

    esperados = MIME_POR_EXT.get(ext)
    if esperados and mime not in esperados:
        raise ValidationError(f"El contenido ({mime}) no coincide con la extensión {ext}.")
