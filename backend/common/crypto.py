"""Acceso al cifrador Fernet del proyecto (clave ``SECRET_KEY_FERNET``)."""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    key = getattr(settings, "SECRET_KEY_FERNET", None)
    if not key:
        raise ImproperlyConfigured("Falta SECRET_KEY_FERNET.")
    return Fernet(key.encode() if isinstance(key, str) else key)
