"""Configuración key-value y auditoría append-only (DATA PLANE).

Referencia: MODELO_DATOS_SAR §6.12 · SAR_FUNCIONALIDADES §14.2/14.3.
"""
from __future__ import annotations

from django.db import models


class Opcion(models.Model):  # options (helper get_option del origen)
    clave = models.CharField(max_length=120, unique=True, db_index=True)
    valor = models.TextField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.clave


class HistorialCambio(models.Model):  # change_histories (Change_history)
    class Accion(models.TextChoices):
        CREADO = "creado", "Creado"
        ACTUALIZADO = "actualizado", "Actualizado"
        ELIMINADO = "eliminado", "Eliminado"
        RESTAURADO = "restaurado", "Restaurado"
        ASIGNADO = "asignado", "Asignado"
        DESASIGNADO = "desasignado", "Desasignado"
        VISTO = "visto", "Visto"
        LISTADO = "listado", "Listado"

    descripcion = models.TextField()
    modelo = models.CharField(max_length=120, null=True, blank=True)
    modelo_id = models.BigIntegerField(null=True, blank=True)
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True, db_index=True
    )
    accion = models.CharField(max_length=12, choices=Accion.choices, default=Accion.CREADO)
    # Decisión abierta del modelo: diff antes/después (listo pero opcional).
    antes = models.JSONField(null=True, blank=True)
    despues = models.JSONField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["modelo", "modelo_id"])]
        ordering = ["-creado"]
