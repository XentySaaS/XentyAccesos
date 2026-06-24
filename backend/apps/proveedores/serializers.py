"""Serializers de proveedores (catálogo + onboarding)."""
from __future__ import annotations

from rest_framework import serializers

from common.validators import rfc_valido, validar_archivo

from .models import CuentaProveedor, Proveedor

_DOCS = (".pdf", ".jpg", ".jpeg", ".png")


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            "id", "nombre", "razon_social", "rfc", "email", "email_responsable",
            "nombre_responsable", "telefono", "direccion", "file_repse", "file_sua",
            "responsable", "estado",
        ]
        read_only_fields = ["estado"]  # lo gobierna el flujo de onboarding

    def validate_rfc(self, rfc):
        if rfc and not rfc_valido(rfc):
            raise serializers.ValidationError("RFC inválido (estructura o dígito verificador).")
        return (rfc or "").upper().strip() or None

    def validate_file_repse(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=5)
        return f

    def validate_file_sua(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=5)
        return f


class OnboardingProveedorSerializer(serializers.Serializer):
    """Alta de la cuenta del proveedor a partir de una invitación firmada."""

    token = serializers.CharField()
    nombre = serializers.CharField(max_length=160)
    apellidos = serializers.CharField(max_length=160, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    puesto = serializers.CharField(max_length=120, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_email(self, email):
        email = email.lower()
        if CuentaProveedor.objects.filter(email=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese correo.")
        return email
