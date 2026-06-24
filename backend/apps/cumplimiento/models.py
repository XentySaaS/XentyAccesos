"""Cumplimiento SAT 69-B (DATA PLANE): espejo de EFOS y resultados de validación.

Referencia: MODELO_DATOS_SAR §6.11 · SAR_FUNCIONALIDADES §13.
"""
from __future__ import annotations

from django.db import models


class SatEfo(models.Model):  # sat_efos (espejo del CSV oficial)
    rfc = models.CharField(max_length=13, unique=True, db_index=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    situacion = models.CharField(max_length=40)  # Presunto|Definitivo|Desvirtuado|Sentencia Favorable
    meta = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.rfc} ({self.situacion})"


class ConsultaLista69b(models.Model):  # lista_69bs
    tipo = models.IntegerField(default=0)  # 0 = individual, 1 = corrida programada
    creado = models.DateTimeField(auto_now_add=True)


class ResultadoLista69b(models.Model):  # result__lista69bs -> resultados_lista69b
    class Estado(models.IntegerChoices):
        LIMPIO = 0, "Limpio"
        ENCONTRADO = 1, "Encontrado"

    consulta = models.ForeignKey(ConsultaLista69b, on_delete=models.CASCADE, related_name="resultados")
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.CASCADE)
    rfc = models.CharField(max_length=13, null=True, blank=True)
    query_data = models.JSONField(null=True, blank=True)
    estado = models.IntegerField(choices=Estado.choices, default=Estado.LIMPIO)
    creado = models.DateTimeField(auto_now_add=True)
