"""Bitácora de acceso físico (DATA PLANE). Índices por tiempo para reportes a escala.

Referencia: MODELO_DATOS_SAR §6.8 · SAR_FUNCIONALIDADES §9.
"""
from __future__ import annotations

from django.db import models


class RegistroAcceso(models.Model):  # access_logs
    class TipoAcceso(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        DENEGADO = "denegado", "Denegado"

    class Metodo(models.TextChoices):
        QR = "qr", "QR"
        PLACA = "placa", "Placa"
        MANUAL = "manual", "Manual"
        TARJETA = "tarjeta", "Tarjeta"

    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.SET_NULL, null=True, blank=True)
    asistente = models.ForeignKey("citas.AsistenteCita", on_delete=models.SET_NULL, null=True, blank=True)
    evento = models.ForeignKey("eventos.Evento", on_delete=models.SET_NULL, null=True, blank=True)
    cita = models.ForeignKey("citas.Cita", on_delete=models.SET_NULL, null=True, blank=True)
    cajon = models.ForeignKey("eventos.CajonParking", on_delete=models.SET_NULL, null=True, blank=True)
    tipo_acceso = models.CharField(max_length=10, choices=TipoAcceso.choices, default=TipoAcceso.ENTRADA)
    metodo = models.CharField(max_length=10, choices=Metodo.choices, default=Metodo.QR)
    placa_vehiculo = models.CharField(max_length=20, null=True, blank=True)
    hora_entrada = models.DateTimeField(db_index=True)
    hora_salida = models.DateTimeField(null=True, blank=True, db_index=True)
    observaciones = models.TextField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)


class RegistroAccesoParking(models.Model):  # access_log_parkings
    class TipoAcceso(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        DENEGADO = "denegado", "Denegado"

    cajon = models.ForeignKey("eventos.CajonParking", on_delete=models.CASCADE, related_name="registros")
    tipo_acceso = models.CharField(max_length=10, choices=TipoAcceso.choices, default=TipoAcceso.ENTRADA)
    hora_entrada = models.DateTimeField(db_index=True)
    hora_salida = models.DateTimeField(null=True, blank=True)
    personas = models.IntegerField(default=1)
    placa_vehiculo = models.CharField(max_length=20, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
