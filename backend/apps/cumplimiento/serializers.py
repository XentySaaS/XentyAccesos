"""Serializers de cumplimiento 69-B."""
from __future__ import annotations

from rest_framework import serializers

from .models import ResultadoLista69b, SatEfo


class SatEfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SatEfo
        fields = ["id", "rfc", "nombre", "situacion"]


class ResultadoLista69bSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoLista69b
        fields = ["id", "consulta", "proveedor", "rfc", "estado", "query_data", "creado"]
