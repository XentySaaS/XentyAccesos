"""ViewSet de Sanciones (severidad/penalidad solo Administrador)."""
from __future__ import annotations

from rest_framework import viewsets

from apps.config.services import AuditViewSetMixin
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import Sancion
from .serializers import SancionSerializer


class SancionViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Sancion.objects.all().order_by("-creado")
    serializer_class = SancionSerializer
    permission_classes = [
        *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("sanciones"),
        RequiereRol("administrador", "guardia"),
    ]
    filterset_fields = ["empleado", "penalidad", "severidad"]
