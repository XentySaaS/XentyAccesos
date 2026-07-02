"""Serializer de Sancion. Suspensión exige fecha_inicio y fecha_fin (SAR_FUNC §10)."""
from __future__ import annotations

from rest_framework import serializers

from .models import Sancion

# Campos que solo el Administrador puede fijar/editar (SAR_FUNC §10; el original WarningResource
# marca severity/penalty como visible/enabled solo isAdmin()). El guardia captura empleado, evento
# y motivo; la severidad, penalidad y fechas de suspensión las define el admin.
CAMPOS_SOLO_ADMIN = ("severidad", "penalidad", "fecha_inicio", "fecha_fin")


class SancionSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source="empleado.nombre", read_only=True)
    evento_nombre = serializers.CharField(source="evento.nombre", read_only=True, default=None)

    class Meta:
        model = Sancion
        fields = [
            "id", "empleado", "empleado_nombre", "evento", "evento_nombre", "cita",
            "severidad", "penalidad", "motivo", "fecha_inicio", "fecha_fin", "creado",
        ]
        read_only_fields = ["creado", "empleado_nombre", "evento_nombre"]

    def _es_admin(self) -> bool:
        user = getattr(self.context.get("request"), "user", None)
        return getattr(user, "rol", None) == "administrador"

    def validate(self, attrs):
        # Un no-admin no puede fijar ni cambiar los campos admin-only: se ignora lo que envíe
        # (en alta quedan nulos; en edición conservan el valor puesto por el admin).
        if not self._es_admin():
            for campo in CAMPOS_SOLO_ADMIN:
                attrs.pop(campo, None)

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
