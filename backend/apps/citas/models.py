"""Citas (DATA PLANE) — visitas puntuales de proveedor (tipo 0) o directas (tipo 1).

El asistente referencia a un Contacto o Empleado vía ``GenericForeignKey`` (el origen tenía un
``person_id`` polimórfico sin FK). La INE del asistente se cifra en reposo (REMEDIACION §A2).

Referencia: MODELO_DATOS_SAR §6.7 · SAR_FUNCIONALIDADES §7.
"""
from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from common.fields import EncryptedCharField, EncryptedJSONField


class Contacto(models.Model):  # contacts
    nombre = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre


class Cita(models.Model):  # appointments
    class Tipo(models.IntegerChoices):
        PROVEEDOR = 0, "Proveedor"
        DIRECTA = 1, "Directa"

    class TipoCita(models.TextChoices):
        PROGRAMADA = "programada", "Programada"
        WALK_IN = "walk_in", "Walk-in"
        EMERGENCIA = "emergencia", "Emergencia"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"

    creado_por_usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.PROTECT, related_name="citas_creadas"
    )
    asignado_a = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="citas_asignadas",
    )
    nombre = models.CharField(max_length=200, null=True, blank=True)
    detalles = models.TextField(null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    limite = models.IntegerField(null=True, blank=True)
    tipo = models.IntegerField(choices=Tipo.choices, default=Tipo.PROVEEDOR)
    tipo_cita = models.CharField(max_length=12, choices=TipoCita.choices, default=TipoCita.PROGRAMADA)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    protocolo = models.ForeignKey("recintos.Protocolo", on_delete=models.PROTECT, null=True, blank=True)
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.SET_NULL, null=True, blank=True)
    recinto = models.ForeignKey("recintos.Recinto", on_delete=models.PROTECT)
    ubicacion = models.ForeignKey(
        "recintos.Ubicacion", on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_ubicacion"
    )
    punto_acceso = models.ForeignKey(
        "recintos.Ubicacion", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="citas_punto_acceso",
    )
    acceso = models.ForeignKey("recintos.Acceso", on_delete=models.SET_NULL, null=True, blank=True)
    empleados = models.ManyToManyField("empleados.Empleado", through="EmpleadoCita")
    areas_autorizadas = models.ManyToManyField(
        "recintos.AreaAutorizada", through="AreaAutorizadaCita", related_name="citas"
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre or f"Cita {self.pk}"


class EmpleadoCita(models.Model):  # employee_appointment
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE)
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("empleado", "cita")]


class AreaAutorizadaCita(models.Model):  # authorized_areas_appointments
    area = models.ForeignKey("recintos.AreaAutorizada", on_delete=models.CASCADE)
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("area", "cita")]


class AsistenteCita(models.Model):  # assistent_appointments -> asistentes_cita
    class Tipo(models.IntegerChoices):
        CONTACTO = 0, "Contacto"
        EMPLEADO = 1, "Empleado"

    class Estado(models.IntegerChoices):
        PENDIENTE = 0, "Pendiente"
        CONFIRMADO = 1, "Confirmado"
        CANCELADO = 2, "Cancelado"

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name="asistentes")
    nombre = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)  # unique REMOVIDO en origen
    telefono = models.CharField(max_length=30, null=True, blank=True)
    estado = models.IntegerField(choices=Estado.choices, default=Estado.PENDIENTE)
    # person_id polimórfico (contacts|employees) -> GenericForeignKey explícita (FIX)
    tipo = models.IntegerField(choices=Tipo.choices, default=Tipo.CONTACTO)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    persona = GenericForeignKey("content_type", "object_id")
    # INE / identificación — PII cifrada (Fernet):
    requiere_ine = models.BooleanField(default=True)
    ine_capturado = models.BooleanField(default=False)
    ine_data = EncryptedJSONField(null=True, blank=True)
    path_ine = models.FileField(upload_to="citas/ine/", null=True, blank=True)  # disco PRIVADO
    tipo_identificacion = models.PositiveSmallIntegerField(null=True, blank=True)
    numero_identificacion = EncryptedCharField(max_length=64, null=True, blank=True)
    estado_adicional = models.PositiveSmallIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre
