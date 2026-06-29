"""Serializers de configuración y auditoría."""
from __future__ import annotations

from rest_framework import serializers

from .models import HistorialCambio, Opcion


class OpcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opcion
        fields = ["id", "clave", "valor"]


class HistorialCambioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()

    def get_usuario_nombre(self, obj) -> str:
        if obj.usuario:
            nombre = getattr(obj.usuario, "nombre", "") or ""
            return nombre or obj.usuario.email
        return "Sistema"

    class Meta:
        model = HistorialCambio
        fields = [
            "id", "descripcion", "modelo", "modelo_id",
            "usuario", "usuario_nombre", "accion", "creado",
            "antes", "despues",
        ]
