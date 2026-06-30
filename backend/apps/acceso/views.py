"""Acceso físico: escáner (guardia) + bitácora con registro de salida."""
from __future__ import annotations

from django.db import connection
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequierePermisoPersonalizado, RequiereRol

from .models import RegistroAcceso
from .serializers import RegistroAccesoSerializer
from .services import procesar_escaneo

_SCANNER = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("acceso"),
    RequiereRol("guardia", "administrador", "recepcion", "usuario"),
    RequierePermisoPersonalizado("acceso"),
]
_BITACORA = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("acceso"),
    RequiereRol("guardia", "administrador", "editor", "recepcion", "usuario"),
    RequierePermisoPersonalizado("acceso"),
]


class EscanearView(APIView):
    """POST /api/acceso/escanear/ {qr, placa?} — valida y registra el acceso."""

    permission_classes = _SCANNER

    def post(self, request):
        reg, permitido, motivo = procesar_escaneo(
            request.data.get("qr", ""), connection.schema_name, placa=request.data.get("placa")
        )
        return Response({
            "permitido": permitido,
            "motivo": motivo,
            "registro_id": reg.id,
            "tipo_acceso": getattr(reg, "tipo_acceso", None),
        })


class RegistroAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitácora de accesos (solo lectura) + acción de registrar salida."""

    serializer_class = RegistroAccesoSerializer
    permission_classes = _BITACORA
    filterset_fields = ["tipo_acceso", "metodo"]

    def get_queryset(self):
        qs = RegistroAcceso.objects.select_related(
            "empleado", "asistente", "evento", "cita"
        ).order_by("-hora_entrada")
        p = self.request.query_params
        if p.get("fecha_desde"):
            qs = qs.filter(hora_entrada__date__gte=p["fecha_desde"])
        if p.get("fecha_hasta"):
            qs = qs.filter(hora_entrada__date__lte=p["fecha_hasta"])
        return qs

    @action(detail=True, methods=["post"])
    def salida(self, request, pk=None):
        reg = self.get_object()
        reg.hora_salida = timezone.now()
        reg.save(update_fields=["hora_salida"])
        # F7: WhatsApp de confirmación de salida.
        return Response({"hora_salida": reg.hora_salida})
