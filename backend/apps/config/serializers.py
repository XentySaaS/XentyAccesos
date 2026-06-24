"""Serializers de configuración y auditoría."""
from __future__ import annotations

from rest_framework import serializers

from .models import HistorialCambio, Opcion


class OpcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opcion
        fields = ["id", "clave", "valor"]


class HistorialCambioSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialCambio
        fields = ["id", "descripcion", "modelo", "modelo_id", "usuario", "accion", "creado"]
