"""Serializers de la topología de recintos."""

from __future__ import annotations

from rest_framework import serializers

from common.phone import TelefonoField
from common.validators import validar_archivo

from .models import Acceso, AreaAutorizada, Entrada, Protocolo, Recinto, Ubicacion, Zona


class RecintoSerializer(serializers.ModelSerializer):
    telefono = TelefonoField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Recinto
        fields = ["id", "nombre", "descripcion", "telefono", "codigo"]


class ZonaSerializer(serializers.ModelSerializer):
    telefono = TelefonoField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Zona
        fields = ["id", "recinto", "nombre", "descripcion", "telefono"]


class AccesoSerializer(serializers.ModelSerializer):
    telefono = TelefonoField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Acceso
        fields = ["id", "recinto", "nombre", "descripcion", "telefono"]


class UbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ubicacion
        fields = ["id", "zona", "nombre", "descripcion", "padre"]

    def validate(self, attrs):
        # El padre (si se indica) debe pertenecer a la misma zona.
        padre = attrs.get("padre")
        zona = attrs.get("zona") or getattr(self.instance, "zona", None)
        if padre and zona and padre.zona_id != zona.id:
            raise serializers.ValidationError({"padre": "El padre debe ser de la misma zona."})
        return attrs


class EntradaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entrada
        fields = ["id", "acceso", "nombre", "descripcion", "padre"]

    def validate(self, attrs):
        padre = attrs.get("padre")
        acceso = attrs.get("acceso") or getattr(self.instance, "acceso", None)
        if padre and acceso and padre.acceso_id != acceso.id:
            raise serializers.ValidationError({"padre": "El padre debe ser del mismo acceso."})
        return attrs


class AreaAutorizadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaAutorizada
        fields = ["id", "recinto", "nombre", "descripcion", "activo"]


class ProtocoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocolo
        fields = ["id", "nombre", "descripcion", "archivo", "activo"]

    def validate_archivo(self, archivo):
        if archivo:
            validar_archivo(archivo, extensiones=(".pdf",), max_mb=10)
        return archivo
