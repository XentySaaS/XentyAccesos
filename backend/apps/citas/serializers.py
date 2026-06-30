"""Serializers de citas.

La PII de INE no se expone aquí (se captura por el flujo OCR, F4.2).
Tres capas de serialización:
  - CitaListSerializer   → tabla (ligero, solo nombres clave)
  - CitaDetailSerializer → detalle con asistentes anidados
  - CitaSerializer       → escritura (create/update) con invitados embebidos
"""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from apps.empleados.models import Empleado

from .models import AsistenteCita, Cita, Contacto


class ContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacto
        fields = ["id", "nombre", "email", "telefono"]


# ── Asistentes ────────────────────────────────────────────────────────────────

class AsistenteCitaInputSerializer(serializers.Serializer):
    """Entrada al crear/editar una cita con invitados embebidos."""
    nombre = serializers.CharField(max_length=200)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    telefono = serializers.CharField(max_length=30, required=False, allow_null=True, allow_blank=True)
    persona_id = serializers.IntegerField(required=False, allow_null=True)
    tipo = serializers.IntegerField(default=AsistenteCita.Tipo.CONTACTO)


class AsistenteCitaSerializer(serializers.ModelSerializer):
    persona_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = AsistenteCita
        fields = [
            "id", "cita", "nombre", "email", "telefono", "estado", "tipo",
            "persona_id", "requiere_ine", "ine_capturado",
            "tipo_identificacion", "estado_adicional",
        ]
        read_only_fields = ["ine_capturado"]

    def create(self, validated):
        persona_id = validated.pop("persona_id", None)
        if persona_id:
            modelo = Empleado if validated.get("tipo") == AsistenteCita.Tipo.EMPLEADO else Contacto
            validated["content_type"] = ContentType.objects.get_for_model(modelo)
            validated["object_id"] = persona_id
        return super().create(validated)


# ── Cita — lectura ────────────────────────────────────────────────────────────

class CitaListSerializer(serializers.ModelSerializer):
    """Serializer ligero para la tabla: solo campos necesarios para mostrar filas."""
    recinto_nombre = serializers.CharField(source="recinto.nombre", read_only=True)
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre", read_only=True, allow_null=True, default=None
    )
    asignado_a_nombre = serializers.CharField(
        source="asignado_a.nombre", read_only=True, allow_null=True, default=None
    )
    total_asistentes = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id", "nombre", "fecha", "hora_inicio", "hora_fin",
            "tipo", "tipo_cita", "estado",
            "recinto", "recinto_nombre",
            "proveedor", "proveedor_nombre",
            "asignado_a", "asignado_a_nombre",
            "total_asistentes", "creado",
        ]

    def get_total_asistentes(self, obj) -> int:
        return obj.asistentes.count()


class CitaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para el panel de detalle."""
    recinto_nombre = serializers.CharField(source="recinto.nombre", read_only=True)
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre", read_only=True, allow_null=True, default=None
    )
    asignado_a_nombre = serializers.CharField(
        source="asignado_a.nombre", read_only=True, allow_null=True, default=None
    )
    protocolo_nombre = serializers.CharField(
        source="protocolo.nombre", read_only=True, allow_null=True, default=None
    )
    ubicacion_nombre = serializers.CharField(
        source="ubicacion.nombre", read_only=True, allow_null=True, default=None
    )
    acceso_nombre = serializers.CharField(
        source="acceso.nombre", read_only=True, allow_null=True, default=None
    )
    asistentes = AsistenteCitaSerializer(many=True, read_only=True)

    class Meta:
        model = Cita
        fields = [
            "id", "nombre", "detalles", "fecha", "hora_inicio", "hora_fin", "limite",
            "tipo", "tipo_cita", "estado",
            "recinto", "recinto_nombre",
            "ubicacion", "ubicacion_nombre",
            "acceso", "acceso_nombre",
            "protocolo", "protocolo_nombre",
            "proveedor", "proveedor_nombre",
            "asignado_a", "asignado_a_nombre",
            "asistentes", "creado", "actualizado",
        ]


# ── Cita — escritura ──────────────────────────────────────────────────────────

class CitaSerializer(serializers.ModelSerializer):
    """Serializer de escritura. Acepta lista de invitados embebida en ``asistentes_input``."""
    asistentes_input = AsistenteCitaInputSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Cita
        fields = [
            "id", "nombre", "detalles", "fecha", "hora_inicio", "hora_fin", "limite",
            "tipo", "tipo_cita", "estado", "creado_por_usuario", "asignado_a", "protocolo",
            "proveedor", "recinto", "ubicacion", "punto_acceso", "acceso",
            "asistentes_input",
        ]
        read_only_fields = ["creado_por_usuario"]

    def validate(self, attrs):
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

    def create(self, validated):
        asistentes_data = validated.pop("asistentes_input", [])
        cita = super().create(validated)
        self._guardar_asistentes(cita, asistentes_data)
        return cita

    def update(self, instance, validated):
        asistentes_data = validated.pop("asistentes_input", None)
        cita = super().update(instance, validated)
        if asistentes_data is not None:
            self._guardar_asistentes(cita, asistentes_data)
        return cita

    @staticmethod
    def _guardar_asistentes(cita: Cita, data: list) -> None:
        """Upserts contactos y crea registros AsistenteCita."""
        for a in data:
            persona_id = a.get("persona_id")
            tipo = a.get("tipo", AsistenteCita.Tipo.CONTACTO)
            nombre = a["nombre"]
            email = a.get("email") or None
            telefono = a.get("telefono") or None

            if not persona_id:
                qs = Contacto.objects.filter(nombre=nombre)
                if email:
                    qs = qs.filter(email=email)
                contacto = qs.first() or Contacto.objects.create(
                    nombre=nombre, email=email, telefono=telefono
                )
                persona_id = contacto.id
                tipo = AsistenteCita.Tipo.CONTACTO

            ct = ContentType.objects.get_for_model(
                Empleado if tipo == AsistenteCita.Tipo.EMPLEADO else Contacto
            )
            AsistenteCita.objects.create(
                cita=cita,
                nombre=nombre,
                email=email,
                telefono=telefono,
                tipo=tipo,
                content_type=ct,
                object_id=persona_id,
            )
