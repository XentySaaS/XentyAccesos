"""Mensajería WhatsApp (DATA PLANE): campañas segmentadas y sus destinatarios.

Envío por Celery con reintentos; UltraMsg tras interfaz (credenciales por entorno, REMEDIATION §C2).

Referencia: MODELO_DATOS_SAR §6.10 · SAR_FUNCIONALIDADES §12.
"""

from __future__ import annotations

from django.db import models


class Mensaje(models.Model):  # messages
    class Segmento(models.TextChoices):
        RECINTO = "recinto", "Recinto"
        ZONA = "zona", "Zona"
        EVENTO = "evento", "Evento"
        TODOS_EVENTOS = "todos_eventos", "Todos los eventos"
        TODOS_RECINTOS = "todos_recintos", "Todos los recintos"
        RECINTOS_Y_ZONAS = "recintos_y_zonas", "Recintos y zonas"

    class Estado(models.IntegerChoices):
        PENDIENTE = 0, "Pendiente"
        EN_PROGRESO = 1, "En progreso"
        CANCELADO = 2, "Cancelado"
        COMPLETADO = 3, "Completado"

    cuerpo = models.TextField()
    archivo = models.FileField(upload_to="mensajes/", null=True, blank=True)
    segmento = models.CharField(max_length=20, choices=Segmento.choices, default=Segmento.RECINTO)
    segmento_id = models.BigIntegerField(null=True, blank=True)  # id de recinto/zona/evento
    estado = models.IntegerField(choices=Estado.choices, default=Estado.PENDIENTE)
    progreso = models.FloatField(default=0)
    creado_por = models.ForeignKey("accounts.Usuario", on_delete=models.SET_NULL, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)


class DestinatarioMensaje(models.Model):  # message_recipients
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIADO = "enviado", "Enviado"
        FALLIDO = "fallido", "Fallido"

    mensaje = models.ForeignKey(Mensaje, on_delete=models.CASCADE, related_name="destinatarios")
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )  # FIX: índice para seguimiento de progreso
    external_id = models.CharField(max_length=64, null=True, blank=True)  # id de UltraMsg
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
