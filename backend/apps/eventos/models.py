"""Eventos (DATA PLANE, schema por tenant) — núcleo operativo.

F3.1 cubre el Evento, su máquina de estados y sus verificadores. ``EventoProveedor``, parking,
pivotes evento↔documento y la asignación masiva llegan en F3.2.

Referencia: MODELO_DATOS_SAR §6.6 · SAR_FUNCIONALIDADES §6.
"""
from __future__ import annotations

import uuid

from django.db import models


class Evento(models.Model):  # events
    class Estado(models.TextChoices):
        PROGRAMADO = "programado", "Programado"
        EN_CURSO = "en_curso", "En curso"
        COMPLETADO = "completado", "Completado"
        CANCELADO = "cancelado", "Cancelado"

    # Transiciones permitidas (manuales). Completado/cancelado son terminales.
    TRANSICIONES = {
        Estado.PROGRAMADO: {Estado.EN_CURSO, Estado.CANCELADO},
        Estado.EN_CURSO: {Estado.COMPLETADO, Estado.CANCELADO},
        Estado.COMPLETADO: set(),
        Estado.CANCELADO: set(),
    }

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(
        "accounts.Usuario", on_delete=models.PROTECT, related_name="eventos"
    )
    recinto = models.ForeignKey("recintos.Recinto", on_delete=models.PROTECT)
    protocolo = models.ForeignKey("recintos.Protocolo", on_delete=models.PROTECT, null=True, blank=True)
    vigencia_inicio = models.DateField()  # era start_time (DATE)
    vigencia_fin = models.DateField()     # era end_time (DATE); valida fin >= inicio
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROGRAMADO)
    verificadores = models.ManyToManyField(
        "accounts.Usuario", through="VerificadorEvento", related_name="eventos_a_verificar"
    )
    areas_autorizadas = models.ManyToManyField(
        "recintos.AreaAutorizada", through="AreaAutorizadaEvento", related_name="eventos"
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def puede_transicionar(self, nuevo: str) -> bool:
        return nuevo in self.TRANSICIONES.get(self.estado, set())

    def __str__(self) -> str:
        return self.nombre


class VerificadorEvento(models.Model):  # verifiers_events
    usuario = models.ForeignKey("accounts.Usuario", on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("usuario", "evento")]


class EventoProveedor(models.Model):  # event_suppliers
    """Invitación de un proveedor a un evento, con su configuración (zona/acceso/parking/límite)."""

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="proveedores")
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.CASCADE)
    protocolo = models.ForeignKey("recintos.Protocolo", on_delete=models.SET_NULL, null=True, blank=True)
    zona = models.ForeignKey("recintos.Zona", on_delete=models.SET_NULL, null=True, blank=True)
    acceso = models.ForeignKey("recintos.Acceso", on_delete=models.SET_NULL, null=True, blank=True)
    ubicacion = models.ForeignKey(
        "recintos.Ubicacion", on_delete=models.SET_NULL, null=True, blank=True, related_name="es_ubicacion"
    )
    punto_acceso = models.ForeignKey(
        "recintos.Ubicacion", on_delete=models.SET_NULL, null=True, blank=True, related_name="es_punto_acceso"
    )
    limite = models.IntegerField(default=0)  # 0 = sin límite
    requiere_parking = models.BooleanField(default=False)
    parking = models.CharField(max_length=120, null=True, blank=True)  # nombre del estacionamiento
    cajones_parking = models.IntegerField(default=0)
    notas = models.TextField(null=True, blank=True)
    empleados = models.ManyToManyField("empleados.Empleado", through="EmpleadoEventoProveedor")
    areas_autorizadas = models.ManyToManyField(
        "recintos.AreaAutorizada", through="AreaAutorizadaEventoProveedor",
        related_name="eventos_proveedor",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("evento", "proveedor")]

    def __str__(self) -> str:
        return f"{self.evento} · {self.proveedor}"


class EmpleadoEventoProveedor(models.Model):  # employee_event_supplier
    class StatusDocs(models.IntegerChoices):
        PENDIENTES = 0, "Docs pendientes"
        CUMPLE = 1, "Cumple"

    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE)
    evento_proveedor = models.ForeignKey(EventoProveedor, on_delete=models.CASCADE, related_name="asignaciones")
    statusdocs = models.IntegerField(choices=StatusDocs.choices, default=StatusDocs.PENDIENTES)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("empleado", "evento_proveedor")]


class CajonParking(models.Model):  # parking_event_suppliers
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)  # va en el QR
    evento_proveedor = models.ForeignKey(EventoProveedor, on_delete=models.CASCADE, related_name="cajones")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)


class EventoGrupoDocumentos(models.Model):  # event_group_documents
    class TypeValidation(models.IntegerChoices):
        AL_MENOS_UNO = 0, "Al menos uno"
        TODOS = 1, "Todos"

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="grupos_documentos")
    grupo = models.ForeignKey("documentos.GrupoDocumentos", on_delete=models.CASCADE)
    type_validation = models.IntegerField(
        choices=TypeValidation.choices, default=TypeValidation.AL_MENOS_UNO
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("evento", "grupo")]


class EventoTipoDocumento(models.Model):  # event_list_document
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="tipos_documento")
    tipo_documento = models.ForeignKey("documentos.TipoDocumento", on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("evento", "tipo_documento")]


class AreaAutorizadaEvento(models.Model):  # authorized_areas_events
    area = models.ForeignKey("recintos.AreaAutorizada", on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("area", "evento")]


class AreaAutorizadaEventoProveedor(models.Model):  # authorized_areas_event_supppliers (typo corregido)
    area = models.ForeignKey("recintos.AreaAutorizada", on_delete=models.CASCADE)
    evento_proveedor = models.ForeignKey(EventoProveedor, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("area", "evento_proveedor")]
