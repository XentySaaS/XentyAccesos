"""Serializer de Evento (estado y creador gobernados por el servidor)."""
from __future__ import annotations

from rest_framework import serializers

from .models import Evento


class EventoSerializer(serializers.ModelSerializer):
    verificadores = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Evento
        fields = [
            "id", "nombre", "descripcion", "creado_por", "recinto", "protocolo",
            "vigencia_inicio", "vigencia_fin", "hora_inicio", "hora_fin", "estado", "verificadores",
        ]
        read_only_fields = ["creado_por", "estado", "verificadores"]

    def validate(self, attrs):
        inicio = attrs.get("vigencia_inicio") or getattr(self.instance, "vigencia_inicio", None)
        fin = attrs.get("vigencia_fin") or getattr(self.instance, "vigencia_fin", None)
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError(
                {"vigencia_fin": "La vigencia final no puede ser anterior a la inicial."}
            )
        return attrs
