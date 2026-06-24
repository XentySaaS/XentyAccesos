"""Serializers de citas. La PII de INE no se expone aquí (se captura por el flujo OCR, F4.2)."""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from apps.empleados.models import Empleado

from .models import AsistenteCita, Cita, Contacto


class ContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacto
        fields = ["id", "nombre", "email", "telefono"]


class CitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = [
            "id", "nombre", "detalles", "fecha", "hora_inicio", "hora_fin", "limite",
            "tipo", "tipo_cita", "estado", "creado_por_usuario", "asignado_a", "protocolo",
            "proveedor", "recinto", "ubicacion", "punto_acceso", "acceso",
        ]
        read_only_fields = ["creado_por_usuario"]

    def validate(self, attrs):
        # Cascada Recinto -> Zona -> Ubicación -> Acceso (SAR_FUNC §7.1).
        recinto = attrs.get("recinto") or getattr(self.instance, "recinto", None)
        ubic = attrs.get("ubicacion")
        acc = attrs.get("acceso")
        pa = attrs.get("punto_acceso")
        if recinto and ubic and ubic.zona.recinto_id != recinto.id:
            raise serializers.ValidationError({"ubicacion": "No pertenece al recinto."})
        if recinto and pa and pa.zona.recinto_id != recinto.id:
            raise serializers.ValidationError({"punto_acceso": "No pertenece al recinto."})
        if recinto and acc and acc.recinto_id != recinto.id:
            raise serializers.ValidationError({"acceso": "No pertenece al recinto."})
        return attrs


class AsistenteCitaSerializer(serializers.ModelSerializer):
    persona_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = AsistenteCita
        fields = [
            "id", "cita", "nombre", "email", "telefono", "estado", "tipo",
            "persona_id", "requiere_ine", "ine_capturado", "tipo_identificacion", "estado_adicional",
        ]
        read_only_fields = ["ine_capturado"]  # lo fija el flujo OCR; nunca se expone ine_data

    def create(self, validated):
        persona_id = validated.pop("persona_id", None)
        if persona_id:
            modelo = Empleado if validated.get("tipo") == AsistenteCita.Tipo.EMPLEADO else Contacto
            validated["content_type"] = ContentType.objects.get_for_model(modelo)
            validated["object_id"] = persona_id
        return super().create(validated)
