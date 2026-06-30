"""ViewSets CRUD de la topología de recintos (rol Administrador, módulo 'recintos')."""
from __future__ import annotations

from rest_framework import viewsets

from apps.config.services import AuditViewSetMixin
from common.permissions import PERMISOS_BASE, RequiereModulo, RequiereRol

from .models import Acceso, AreaAutorizada, Entrada, Protocolo, Recinto, Ubicacion, Zona
from .serializers import (
    AccesoSerializer,
    AreaAutorizadaSerializer,
    EntradaSerializer,
    ProtocoloSerializer,
    RecintoSerializer,
    UbicacionSerializer,
    ZonaSerializer,
)

_PERMS = [*PERMISOS_BASE(), RequiereModulo("recintos"), RequiereRol("administrador")]


class _BaseViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    permission_classes = _PERMS


class RecintoViewSet(_BaseViewSet):
    queryset = Recinto.objects.all().order_by("id")
    serializer_class = RecintoSerializer
    filterset_fields = ["codigo"]
    search_fields = ["nombre", "codigo"]


class ZonaViewSet(_BaseViewSet):
    queryset = Zona.objects.all().order_by("id")
    serializer_class = ZonaSerializer
    filterset_fields = ["recinto"]


class AccesoViewSet(_BaseViewSet):
    queryset = Acceso.objects.all().order_by("id")
    serializer_class = AccesoSerializer
    filterset_fields = ["recinto"]


class UbicacionViewSet(_BaseViewSet):
    queryset = Ubicacion.objects.all().order_by("id")
    serializer_class = UbicacionSerializer
    filterset_fields = ["zona", "padre"]


class EntradaViewSet(_BaseViewSet):
    queryset = Entrada.objects.all().order_by("id")
    serializer_class = EntradaSerializer
    filterset_fields = ["acceso", "padre"]


class AreaAutorizadaViewSet(_BaseViewSet):
    queryset = AreaAutorizada.objects.all().order_by("id")
    serializer_class = AreaAutorizadaSerializer
    filterset_fields = ["recinto", "activo"]


class ProtocoloViewSet(_BaseViewSet):
    queryset = Protocolo.objects.all().order_by("id")
    serializer_class = ProtocoloSerializer
    filterset_fields = ["activo"]
