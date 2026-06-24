"""Sanciones a empleados (DATA PLANE). Una sanción activa bloquea el acceso (SAR_FUNC §10).

``severidad`` y ``penalidad`` solo las edita el Administrador; Suspensión exige fechas.

Referencia: MODELO_DATOS_SAR §6.9.
"""
from __future__ import annotations

from django.db import models


class Sancion(models.Model):  # warnings
    class Severidad(models.TextChoices):
        BAJO = "bajo", "Bajo"
        MEDIO = "medio", "Medio"
        ALTO = "alto", "Alto"

    class Penalidad(models.TextChoices):
        ADVERTENCIA = "advertencia", "Advertencia"
        SUSPENSION = "suspension", "Suspensión"
        BAJA = "baja", "Baja"

    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE, related_name="sanciones")
    evento = models.ForeignKey("eventos.Evento", on_delete=models.SET_NULL, null=True, blank=True)
    cita = models.ForeignKey("citas.Cita", on_delete=models.SET_NULL, null=True, blank=True)
    severidad = models.CharField(max_length=8, choices=Severidad.choices, null=True, blank=True)
    penalidad = models.CharField(max_length=12, choices=Penalidad.choices, null=True, blank=True)
    motivo = models.TextField()
    fecha_inicio = models.DateField(null=True, blank=True)  # obligatoria si penalidad=Suspensión
    fecha_fin = models.DateField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
