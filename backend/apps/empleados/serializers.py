"""Serializer de Empleado (el proveedor lo asigna el servidor según el actor)."""

from __future__ import annotations

from rest_framework import serializers

from common.phone import TelefonoField

from .models import Empleado


class EmpleadoSerializer(serializers.ModelSerializer):
    telefono = TelefonoField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Empleado
        fields = ["id", "proveedor", "nombre", "email", "telefono", "foto", "estado"]
        read_only_fields = ["proveedor"]  # se fija desde el actor autenticado
