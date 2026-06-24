"""Serializers de la bitácora de acceso."""
from __future__ import annotations

from rest_framework import serializers

from .models import RegistroAcceso, RegistroAccesoParking


class RegistroAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAcceso
        fields = "__all__"


class RegistroAccesoParkingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAccesoParking
        fields = "__all__"
