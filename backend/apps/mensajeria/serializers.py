"""Serializer de campañas de mensajería."""

from __future__ import annotations

from rest_framework import serializers

from .models import DestinatarioMensaje, Mensaje


class MensajeSerializer(serializers.ModelSerializer):
    total_destinatarios = serializers.SerializerMethodField()

    class Meta:
        model = Mensaje
        fields = [
            "id",
            "cuerpo",
            "archivo",
            "segmento",
            "segmento_id",
            "estado",
            "progreso",
            "creado_por",
            "creado",
            "total_destinatarios",
        ]
        read_only_fields = ["estado", "progreso", "creado_por", "creado"]

    def get_total_destinatarios(self, obj) -> int:
        return DestinatarioMensaje.objects.filter(mensaje=obj).count()
