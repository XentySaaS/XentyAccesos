"""Validación de archivos subidos (REMEDIACION §A3): extensión + tamaño + MIME real.

El nombre lo asigna el servidor (nunca ``getClientOriginalName``). El MIME se valida con
python-magic cuando libmagic está disponible (sí en el contenedor); si no, degrada a
extensión+tamaño para no romper en entornos sin la librería nativa.
"""
from __future__ import annotations

import os

from django.core.exceptions import ValidationError

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
