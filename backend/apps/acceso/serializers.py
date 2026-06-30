"""Serializers de la bitácora de acceso."""
from __future__ import annotations

from rest_framework import serializers

from .models import RegistroAcceso, RegistroAccesoParking


class RegistroAccesoSerializer(serializers.ModelSerializer):
    persona = serializers.SerializerMethodField()
    titulo = serializers.SerializerMethodField()
    tipo_registro = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAcceso
        fields = [
            "id", "tipo_acceso", "metodo",
            "hora_entrada", "hora_salida", "placa_vehiculo", "observaciones",
            "empleado", "asistente", "evento", "cita",
            "persona", "titulo", "tipo_registro", "creado",
        ]

    def get_persona(self, obj) -> str:
        if obj.asistente_id:
            return getattr(obj.asistente, "nombre", None) or "—"
        if obj.empleado_id:
            return getattr(obj.empleado, "nombre", None) or "—"
        return "—"

    def get_titulo(self, obj) -> str:
        if obj.cita_id:
            return getattr(obj.cita, "nombre", None) or f"Cita #{obj.cita_id}"
        if obj.evento_id:
            return getattr(obj.evento, "nombre", None) or f"Evento #{obj.evento_id}"
        return "—"

    def get_tipo_registro(self, obj) -> str:
        if obj.cita_id:
            return "cita"
        if obj.evento_id:
            return "evento"
        return "manual"


class RegistroAccesoParkingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAccesoParking
        fields = "__all__"
