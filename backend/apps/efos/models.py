"""Padrón EFOS del SAT (69-B) — COMPARTIDO entre todos los tenants (schema público).

Es un espejo del listado público del SAT, idéntico para todos los tenants: se guarda UNA sola vez
en el esquema ``public`` (app en ``SHARED_APPS``) en vez de duplicar ~14k filas por cada tenant.
Así la descarga/importación mensual corre una vez y no se sobrecarga la base.

La VALIDACIÓN sigue siendo por tenant: cada tenant lee este padrón compartido (visible vía el
``public`` del search_path) y escribe sus resultados (``ResultadoLista69b``) en su propio schema.
"""
from __future__ import annotations

from django.db import models


class SatEfo(models.Model):  # sat_efos (padrón global, schema público)
    rfc = models.CharField(max_length=13, unique=True, db_index=True)
    # La razón social del SAT puede superar los 500 caracteres → TextField sin límite fijo.
    nombre = models.TextField(null=True, blank=True)
    situacion = models.CharField(max_length=60)  # Presunto|Definitivo|Desvirtuado|Sentencia Favorable
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.rfc} ({self.situacion})"
