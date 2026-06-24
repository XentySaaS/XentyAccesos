"""Configuración, auditoría y reportes (dashboard, calendario, export Excel)."""
from __future__ import annotations

from datetime import date

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereRol

from .models import HistorialCambio, Opcion
from .serializers import HistorialCambioSerializer, OpcionSerializer

_ADMIN = [*PERMISOS_BASE(), ContextoAcceso, RequiereRol("administrador")]


class OpcionViewSet(viewsets.ModelViewSet):
    queryset = Opcion.objects.all().order_by("clave")
    serializer_class = OpcionSerializer
    permission_classes = _ADMIN
    filterset_fields = ["clave"]


class HistorialCambioViewSet(viewsets.ReadOnlyModelViewSet):
    """Auditoría append-only, paginada (corrige M4) e indexada por usuario y (modelo, modelo_id)."""

    queryset = HistorialCambio.objects.all()
    serializer_class = HistorialCambioSerializer
    permission_classes = _ADMIN
    filterset_fields = ["modelo", "usuario", "accion"]


class DashboardView(APIView):
    permission_classes = _ADMIN

    def get(self, request):
        from apps.acceso.models import RegistroAcceso
        from apps.eventos.models import EmpleadoEventoProveedor, Evento

        hoy = date.today()
        vigentes = (
            Evento.objects.filter(vigencia_inicio__lte=hoy, vigencia_fin__gte=hoy)
            .exclude(estado=Evento.Estado.CANCELADO).count()
        )
        invitados = EmpleadoEventoProveedor.objects.count()
        ingresados = (
            RegistroAcceso.objects.filter(
                tipo_acceso=RegistroAcceso.TipoAcceso.ENTRADA, empleado__isnull=False
            ).values("empleado").distinct().count()
        )
        return Response({
            "eventos_vigentes": vigentes,
            "invitados": invitados,
            "ingresados": ingresados,
            "pendientes_por_ingresar": max(invitados - ingresados, 0),
        })


class CalendarioView(APIView):
    permission_classes = _ADMIN

    def get(self, request):
        from apps.citas.models import Cita
        from apps.eventos.models import Evento

        desde = request.query_params.get("desde") or str(date.today())
        hasta = request.query_params.get("hasta") or str(date.today())
        eventos = Evento.objects.filter(vigencia_inicio__lte=hasta, vigencia_fin__gte=desde)
        citas = Cita.objects.filter(fecha__range=[desde, hasta])
        return Response({
            "eventos": [
                {"id": e.id, "nombre": e.nombre, "inicio": e.vigencia_inicio, "fin": e.vigencia_fin}
                for e in eventos
            ],
            "citas": [{"id": c.id, "nombre": c.nombre, "fecha": c.fecha} for c in citas],
        })


class ExportarAccesosView(APIView):
    """GET /api/reportes/accesos.xlsx — exporta la bitácora de accesos a Excel."""

    permission_classes = _ADMIN

    def get(self, request):
        from openpyxl import Workbook

        from apps.acceso.models import RegistroAcceso

        wb = Workbook()
        ws = wb.active
        ws.title = "Accesos"
        ws.append(["ID", "Empleado", "Evento", "Cita", "Tipo", "Método", "Entrada", "Salida"])
        for r in RegistroAcceso.objects.all().order_by("-hora_entrada")[:5000]:
            ws.append([
                r.id, r.empleado_id, r.evento_id, r.cita_id, r.tipo_acceso, r.metodo,
                r.hora_entrada.isoformat() if r.hora_entrada else "",
                r.hora_salida.isoformat() if r.hora_salida else "",
            ])
        resp = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = 'attachment; filename="accesos.xlsx"'
        wb.save(resp)
        return resp
