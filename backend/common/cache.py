"""Aislamiento de cache por tenant (REMEDIACION §A5).

Toda clave se prefija con el schema activo, de modo que dos tenants nunca comparten entradas de
cache (corrige el ``CacheTenancyBootstrapper`` comentado del origen).
"""
from __future__ import annotations

from django.db import connection


def tenant_key_func(key, key_prefix, version):
    schema = getattr(connection, "schema_name", None) or "public"
    return f"{schema}:{key_prefix}:{version}:{key}"
