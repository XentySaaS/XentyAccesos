"""Serializer de Evento (estado y creador gobernados por el servidor)."""

from __future__ import annotations

from rest_framework import serializers

from apps.recintos.models import AreaAutorizada

from .models import (
    AreaAutorizadaEventoProveedor,
    EmpleadoEventoProveedor,
    Evento,
    EventoGrupoDocumentos,
    EventoProveedor,
)


class EventoSerializer(serializers.ModelSerializer):
    verificadores = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    grupos_documentos = serializers.SerializerMethodField()
    recinto_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = [
            "id",
            "nombre",
            "descripcion",
            "creado_por",
            "recinto",
            "recinto_nombre",
            "protocolo",
            "vigencia_inicio",
            "vigencia_fin",
            "hora_inicio",
            "hora_fin",
            "estado",
            "verificadores",
            "grupos_documentos",
        ]
        read_only_fields = ["creado_por", "estado", "verificadores"]

    def get_recinto_nombre(self, obj) -> str:
        return obj.recinto.nombre if obj.recinto_id else ""

    def get_grupos_documentos(self, obj) -> list:
        """Grupos de documentos requeridos del evento (para precargar el formulario al editar)."""
        return [
            {"grupo": g.grupo_id, "type_validation": g.type_validation}
            for g in EventoGrupoDocumentos.objects.filter(evento=obj)
        ]

    def validate(self, attrs):
        inicio = attrs.get("vigencia_inicio") or getattr(self.instance, "vigencia_inicio", None)
        fin = attrs.get("vigencia_fin") or getattr(self.instance, "vigencia_fin", None)
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError(
                {"vigencia_fin": "La vigencia final no puede ser anterior a la inicial."}
            )
        return attrs


class EventoProveedorSerializer(serializers.ModelSerializer):
    asignados = serializers.SerializerMethodField()
    proveedor_nombre = serializers.SerializerMethodField()
    zona_nombre = serializers.SerializerMethodField()
    acceso_nombre = serializers.SerializerMethodField()
    # Datos del evento embebidos: el proveedor no puede consultar /api/eventos/ (es solo de Acceso).
    evento_nombre = serializers.SerializerMethodField()
    evento_estado = serializers.SerializerMethodField()
    evento_descripcion = serializers.SerializerMethodField()
    vigencia_inicio = serializers.SerializerMethodField()
    vigencia_fin = serializers.SerializerMethodField()
    hora_inicio = serializers.SerializerMethodField()
    hora_fin = serializers.SerializerMethodField()
    recinto_nombre = serializers.SerializerMethodField()
    protocolo_nombre = serializers.SerializerMethodField()
    areas_nombres = serializers.SerializerMethodField()
    areas_autorizadas = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=AreaAutorizada.objects.all(),
        required=False,
    )

    class Meta:
        model = EventoProveedor
        fields = [
            "id",
            "evento",
            "evento_nombre",
            "evento_estado",
            "evento_descripcion",
            "vigencia_inicio",
            "vigencia_fin",
            "hora_inicio",
            "hora_fin",
            "recinto_nombre",
            "proveedor",
            "proveedor_nombre",
            "protocolo",
            "protocolo_nombre",
            "zona",
            "zona_nombre",
            "acceso",
            "acceso_nombre",
            "ubicacion",
            "punto_acceso",
            "limite",
            "requiere_parking",
            "parking",
            "cajones_parking",
            "notas",
            "areas_autorizadas",
            "areas_nombres",
            "asignados",
        ]

    def get_asignados(self, obj) -> int:
        return EmpleadoEventoProveedor.objects.filter(evento_proveedor=obj).count()

    def get_proveedor_nombre(self, obj) -> str:
        return obj.proveedor.nombre if obj.proveedor_id else ""

    def get_zona_nombre(self, obj) -> str:
        return obj.zona.nombre if obj.zona_id else ""

    def get_acceso_nombre(self, obj) -> str:
        return obj.acceso.nombre if obj.acceso_id else ""

    def get_evento_nombre(self, obj) -> str:
        return obj.evento.nombre if obj.evento_id else ""

    def get_evento_estado(self, obj) -> str:
        return obj.evento.estado if obj.evento_id else ""

    def get_vigencia_inicio(self, obj):
        return obj.evento.vigencia_inicio if obj.evento_id else None

    def get_vigencia_fin(self, obj):
        return obj.evento.vigencia_fin if obj.evento_id else None

    def get_recinto_nombre(self, obj) -> str:
        return obj.evento.recinto.nombre if obj.evento_id and obj.evento.recinto_id else ""

    def get_evento_descripcion(self, obj) -> str:
        return (obj.evento.descripcion or "") if obj.evento_id else ""

    def get_hora_inicio(self, obj):
        return obj.evento.hora_inicio if obj.evento_id else None

    def get_hora_fin(self, obj):
        return obj.evento.hora_fin if obj.evento_id else None

    def get_protocolo_nombre(self, obj) -> str:
        return obj.protocolo.nombre if obj.protocolo_id else ""

    def get_areas_nombres(self, obj) -> list:
        return list(obj.areas_autorizadas.values_list("nombre", flat=True))

    def validate(self, attrs):
        requiere = attrs.get("requiere_parking")
        if requiere is None and self.instance is not None:
            requiere = self.instance.requiere_parking
        if requiere:
            cajones = attrs.get("cajones_parking")
            if cajones is None and self.instance is not None:
                cajones = self.instance.cajones_parking
            if not cajones or cajones < 1:
                raise serializers.ValidationError(
                    {"cajones_parking": "Indica al menos un cajón si requiere estacionamiento."}
                )
        return attrs

    def create(self, validated):
        areas = validated.pop("areas_autorizadas", None)
        ep = EventoProveedor.objects.create(**validated)
        if areas is not None:
            self._sync_areas(ep, areas)
        return ep

    def update(self, instance, validated):
        areas = validated.pop("areas_autorizadas", None)
        for campo, valor in validated.items():
            setattr(instance, campo, valor)
        instance.save()
        if areas is not None:
            self._sync_areas(instance, areas)
        return instance

    @staticmethod
    def _sync_areas(ep: EventoProveedor, areas) -> None:
        """Reemplaza las áreas autorizadas del proveedor en el evento (pivote sin campos extra)."""
        AreaAutorizadaEventoProveedor.objects.filter(evento_proveedor=ep).delete()
        AreaAutorizadaEventoProveedor.objects.bulk_create(
            [AreaAutorizadaEventoProveedor(evento_proveedor=ep, area=a) for a in areas]
        )
