"""Serializer de Empleado (el proveedor lo asigna el servidor según el actor)."""

from __future__ import annotations

from rest_framework import serializers

from common.phone import TelefonoField

from .models import Empleado


class EmpleadoSerializer(serializers.ModelSerializer):
    # Correo y teléfono son OBLIGATORIOS al dar de alta: validan identidad y el correo detecta
    # duplicados. En PATCH parcial (editar solo foto/estado) no se exigen porque el campo no viaja.
    email = serializers.EmailField(required=True, allow_blank=False)
    telefono = TelefonoField(required=True)

    class Meta:
        model = Empleado
        fields = ["id", "proveedor", "nombre", "email", "telefono", "foto", "estado"]
        read_only_fields = ["proveedor"]  # se fija desde el actor autenticado

    def validate_email(self, value: str) -> str:
        """Normaliza a minúsculas y rechaza duplicados dentro de la MISMA empresa (Proveedor).

        Los empleados se comparten entre las cuentas del mismo Proveedor, así que el duplicado se
        busca por ``proveedor__proveedor_id``. Se ignoran los que están en baja (permite recontratar)
        y a sí mismo al editar.
        """
        value = (value or "").strip().lower()
        request = self.context.get("request")
        empresa_id = getattr(getattr(request, "user", None), "proveedor_id", None)
        if empresa_id:
            dup = Empleado.objects.filter(
                proveedor__proveedor_id=empresa_id, email__iexact=value
            ).exclude(estado=Empleado.Estado.BAJA)
            if self.instance is not None:
                dup = dup.exclude(pk=self.instance.pk)
            if dup.exists():
                raise serializers.ValidationError(
                    "Ya existe un empleado con este correo en tu empresa."
                )
        return value
