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
    """GET /api/reportes/accesos.xlsx — reporte de accesos en Excel (columnas legibles + filtros).

    Reemplaza al ReportAccessResource del origen: mismas columnas (Invitado, Tipo, Evento/Cita,
    Tipo de acceso, Entrada, Salida, Observaciones) y filtros por rango de fechas (``fecha_desde``
    /``fecha_hasta``) y ``tipo_acceso`` — alineados con la bitácora de la pantalla de Accesos.
    """

    permission_classes = _ADMIN

    _ACCESO_LABEL = {"entrada": "Entrada", "denegado": "Denegado"}
    _METODO_LABEL = {"qr": "QR", "placa": "Placa", "manual": "Manual", "tarjeta": "Tarjeta"}

    def get(self, request):
        from openpyxl import Workbook

        from apps.acceso.models import RegistroAcceso

        qs = (
            RegistroAcceso.objects
            .select_related("empleado", "asistente", "evento", "cita")
            .order_by("-hora_entrada")
        )
        p = request.query_params
        if p.get("fecha_desde"):
            qs = qs.filter(hora_entrada__date__gte=p["fecha_desde"])
        if p.get("fecha_hasta"):
            qs = qs.filter(hora_entrada__date__lte=p["fecha_hasta"])
        if p.get("tipo_acceso"):
            qs = qs.filter(tipo_acceso=p["tipo_acceso"])

        def _persona(r):
            if r.asistente_id:
                return getattr(r.asistente, "nombre", None) or "—"
            if r.empleado_id:
                return getattr(r.empleado, "nombre", None) or "—"
            return "—"

        def _tipo(r):
            return "Cita" if r.cita_id else ("Evento" if r.evento_id else "Manual")

        def _titulo(r):
            if r.cita_id:
                return getattr(r.cita, "nombre", None) or f"Cita #{r.cita_id}"
            if r.evento_id:
                return getattr(r.evento, "nombre", None) or f"Evento #{r.evento_id}"
            return "—"

        wb = Workbook()
        ws = wb.active
        ws.title = "Accesos"
        ws.append(["Invitado", "Tipo", "Evento/Cita", "Tipo de acceso", "Método",
                   "Hora entrada", "Hora salida", "Observaciones"])
        for r in qs[:10000]:
            ws.append([
                _persona(r), _tipo(r), _titulo(r),
                self._ACCESO_LABEL.get(r.tipo_acceso, r.tipo_acceso),
                self._METODO_LABEL.get(r.metodo, r.metodo),
                r.hora_entrada.strftime("%Y-%m-%d %H:%M") if r.hora_entrada else "",
                r.hora_salida.strftime("%Y-%m-%d %H:%M") if r.hora_salida else "",
                r.observaciones or "",
            ])
        resp = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = 'attachment; filename="reporte-accesos.xlsx"'
        wb.save(resp)
        return resp
