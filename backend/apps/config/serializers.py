"""Serializers de configuración y auditoría."""

from __future__ import annotations

from rest_framework import serializers

from .models import BitacoraAcceso, HistorialCambio, Opcion


class OpcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opcion
        fields = ["id", "clave", "valor"]


class BitacoraAccesoSerializer(serializers.ModelSerializer):
    evento_label = serializers.CharField(source="get_evento_display", read_only=True)
    contexto_label = serializers.CharField(source="get_contexto_display", read_only=True)

    class Meta:
        model = BitacoraAcceso
        # user_agent crudo queda fuera del API (forense); se expone el resumen `dispositivo`.
        fields = [
            "id",
            "evento",
            "evento_label",
            "contexto",
            "contexto_label",
            "usuario",
            "actor_email",
            "actor_nombre",
            "ip",
            "dispositivo",
            "exito",
            "detalle",
            "creado",
        ]


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
            "id",
            "descripcion",
            "modelo",
            "modelo_id",
            "usuario",
            "usuario_nombre",
            "accion",
            "creado",
            "antes",
            "despues",
        ]
