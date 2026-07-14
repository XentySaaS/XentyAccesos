"""Serializers del contexto acceso (``Usuario``)."""

from __future__ import annotations

import secrets

from rest_framework import serializers

from common.phone import TelefonoField

from .models import PermisoUsuario, Usuario


class UsuarioListSerializer(serializers.ModelSerializer):
    recinto_nombre = serializers.CharField(source="recinto.nombre", read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = [
            "id",
            "email",
            "nombre",
            "rol",
            "activo",
            "recinto",
            "recinto_nombre",
            "telefono",
            "email_verificado",
            "mfa_habilitado",
            "creado",
        ]
        read_only_fields = ["id", "email_verificado", "mfa_habilitado", "creado"]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Crea un usuario nuevo. La contraseña se auto-genera si no se provee."""

    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    telefono = TelefonoField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Usuario
        fields = ["email", "nombre", "rol", "recinto", "telefono", "password"]

    def validate_email(self, value):
        value = value.strip().lower()
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese correo.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None) or secrets.token_urlsafe(12)
        from django.utils import timezone

        user = Usuario.objects.create_user(**validated_data, password=password)
        # El admin que crea usuarios les verifica el email de inmediato.
        user.email_verificado = timezone.now()
        user.save(update_fields=["email_verificado"])
        # Devuelve el password generado una sola vez para que el admin lo comunique.
        user._password_plain = password
        return user


class PermisoUsuarioSerializer(serializers.ModelSerializer):
    modulo_display = serializers.CharField(source="get_modulo_display", read_only=True)

    class Meta:
        model = PermisoUsuario
        fields = ["id", "modulo", "modulo_display", "ver", "crear", "editar", "eliminar"]


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    telefono = TelefonoField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Usuario
        fields = ["nombre", "rol", "recinto", "telefono", "activo"]

    def validate(self, attrs):
        # Baja lógica: registra fecha cuando se desactiva.
        if "activo" in attrs and not attrs["activo"] and self.instance and self.instance.activo:
            from django.utils import timezone

            attrs["fecha_baja"] = timezone.now()
        elif attrs.get("activo") and self.instance and not self.instance.activo:
            attrs["fecha_baja"] = None
        return attrs
