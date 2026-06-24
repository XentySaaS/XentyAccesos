"""Eventos (DATA PLANE, schema por tenant) — núcleo operativo.

F3.1 cubre el Evento, su máquina de estados y sus verificadores. ``EventoProveedor``, parking,
pivotes evento↔documento y la asignación masiva llegan en F3.2.

Referencia: MODELO_DATOS_SAR §6.6 · SAR_FUNCIONALIDADES §6.
"""
from __future__ import annotations

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

    def puede_transicionar(self, nuevo: str) -> bool:
        return nuevo in self.TRANSICIONES.get(self.estado, set())

    def __str__(self) -> str:
        return self.nombre


class VerificadorEvento(models.Model):  # verifiers_events
    usuario = models.ForeignKey("accounts.Usuario", on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("usuario", "evento")]
