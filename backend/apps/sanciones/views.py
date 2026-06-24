"""ViewSet de Sanciones (severidad/penalidad solo Administrador)."""
from __future__ import annotations

from rest_framework import viewsets

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import Sancion
from .serializers import SancionSerializer


class SancionViewSet(viewsets.ModelViewSet):
    queryset = Sancion.objects.all().order_by("-creado")
    serializer_class = SancionSerializer
    permission_classes = [
        *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("sanciones"),
        RequiereRol("administrador"),
    ]
    filterset_fields = ["empleado", "penalidad", "severidad"]
