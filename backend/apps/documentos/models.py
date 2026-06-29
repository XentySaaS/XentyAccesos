"""Catálogo documental y documentos de empleado (DATA PLANE, schema por tenant).

El estado del documento es entero 0/1/2 (el origen tenía drift boolean/int): la lógica de negocio
``checkdocs`` lo usa. Los archivos van a storage privado por schema (REMEDIACION §C5).

Referencia: MODELO_DATOS_SAR §6.5 · SAR_FUNCIONALIDADES §5.
"""
from __future__ import annotations

from django.db import models


class GrupoDocumentos(models.Model):  # group_documents
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre


class TipoDocumento(models.Model):  # list_documents
    grupo = models.ForeignKey(
        GrupoDocumentos, on_delete=models.SET_NULL, null=True, blank=True, related_name="tipos"
    )  # era group_documents_id
    nombre = models.CharField(max_length=160)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre


class Protocolo(models.Model):  # protocols
    """Protocolo operativo del recinto (PDF descargable por el proveedor en su portal)."""

    class Estado(models.TextChoices):
        ACTIVO   = "activo",   "Activo"
        INACTIVO = "inactivo", "Inactivo"

    nombre      = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    archivo     = models.FileField(upload_to="protocolos/", null=True, blank=True)
    estado      = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    creado      = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre


class DocumentoEmpleado(models.Model):  # employee_documents
    class Estado(models.IntegerChoices):
        PENDIENTE = 0, "Pendiente"
        VERIFICADO = 1, "Verificado"
        RECHAZADO = 2, "Rechazado"

    empleado = models.ForeignKey(
        "empleados.Empleado", on_delete=models.CASCADE, related_name="documentos"
    )
    tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT)
    archivo = models.FileField(upload_to="empleados/documentos/")  # storage PRIVADO por schema
    tipo_archivo = models.CharField(max_length=60, null=True, blank=True)
    estado = models.IntegerField(
        choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    motivo_rechazo = models.TextField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.empleado} · {self.tipo_documento}"
