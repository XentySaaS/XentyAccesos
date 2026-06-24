"""Campos de modelo cifrados en reposo con Fernet (AES-128-CBC + HMAC).

Reemplazan el cifrado casero del origen (AES-128-ECB con clave en git, REMEDIACION §C3).
La clave vive en ``settings.SECRET_KEY_FERNET`` (separada de ``SECRET_KEY``), nunca en el código.

El ciphertext se guarda en una columna TEXT (más largo que el claro), por lo que estos campos
NO admiten búsquedas por igualdad: Fernet es no determinístico (IV aleatorio por cifrado). Eso es
deseable para PII (`curp`, `nss`, `ine_data`, tokens) que no se consulta por valor exacto.
"""
from __future__ import annotations

import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Construye (y memoiza) el cifrador desde ``SECRET_KEY_FERNET``.

    Se evalúa de forma perezosa —en el primer save/load— no al importar el módulo, para que
    ``makemigrations`` y los chequeos funcionen aunque la clave aún no sea válida en el entorno.
    """
    key = getattr(settings, "SECRET_KEY_FERNET", None)
    if not key:
        raise ImproperlyConfigured("Falta SECRET_KEY_FERNET para cifrar/descifrar PII.")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:  # clave mal formada
        raise ImproperlyConfigured(
            "SECRET_KEY_FERNET no es una clave Fernet válida (urlsafe base64 de 32 bytes)."
        ) from exc


class EncryptedCharField(models.TextField):
    """Texto corto (CURP, NSS, número de identificación, secretos) cifrado en reposo.

    Acepta ``max_length`` por compatibilidad con el modelo de datos, pero lo ignora a nivel de
    almacenamiento (el ciphertext se guarda en TEXT).
    """

    description = "Texto cifrado en reposo (Fernet)"

    def __init__(self, *args, **kwargs):
        kwargs.pop("max_length", None)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return _fernet().encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Valor heredado en claro o clave rotada: se devuelve tal cual para no romper lecturas.
            return value


class EncryptedJSONField(models.TextField):
    """Estructura JSON (p. ej. ``ine_data`` del OCR) cifrada en reposo."""

    description = "JSON cifrado en reposo (Fernet)"

    def get_prep_value(self, value):
        if value is None:
            return value
        return _fernet().encrypt(json.dumps(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return None
        try:
            return json.loads(_fernet().decrypt(value.encode()).decode())
        except InvalidToken:
            return value
