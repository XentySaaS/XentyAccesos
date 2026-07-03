"""Para el contenedor superadmin-backend: monta el URLconf público (schema 'public')."""

from .prod import *  # noqa: F401,F403

ROOT_URLCONF = "config.urls_public"
