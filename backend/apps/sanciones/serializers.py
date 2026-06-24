"""Serializer de Sancion. Suspensión exige fecha_inicio y fecha_fin (SAR_FUNC §10)."""
from __future__ import annotations

from rest_framework import serializers

from .models import Sancion


class SancionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sancion
        fields = [
            "id", "empleado", "evento", "cita", "severidad", "penalidad",
            "motivo", "fecha_inicio", "fecha_fin", "creado",
        ]
        read_only_fields = ["creado"]

    def validate(self, attrs):
        penalidad = attrs.get("penalidad") or getattr(self.instance, "penalidad", None)
        ini = attrs.get("fecha_inicio") or getattr(self.instance, "fecha_inicio", None)
        fin = attrs.get("fecha_fin") or getattr(self.instance, "fecha_fin", None)
        if penalidad == Sancion.Penalidad.SUSPENSION and not (ini and fin):
            raise serializers.ValidationError(
                "La suspensión requiere fecha_inicio y fecha_fin."
            )
        if ini and fin and fin < ini:
            raise serializers.ValidationError({"fecha_fin": "No puede ser anterior al inicio."})
        return attrs
