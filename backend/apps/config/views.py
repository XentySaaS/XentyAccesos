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
    # El escritorio es la pantalla de inicio de toda la operación, no solo del admin.
    permission_classes = [*PERMISOS_BASE(), ContextoAcceso]

    def get(self, request):
        from django.db.models import Count
        from django.db.models.functions import ExtractHour

        from apps.acceso.models import RegistroAcceso
        from apps.eventos.models import EmpleadoEventoProveedor, Evento

        hoy = date.today()
        ENTRADA = RegistroAcceso.TipoAcceso.ENTRADA

        eventos_vigentes_qs = (
            Evento.objects.filter(vigencia_inicio__lte=hoy, vigencia_fin__gte=hoy)
            .exclude(estado=Evento.Estado.CANCELADO)
        )
        invitados = EmpleadoEventoProveedor.objects.count()
        ingresados = (
            RegistroAcceso.objects.filter(tipo_acceso=ENTRADA, empleado__isnull=False)
            .values("empleado").distinct().count()
        )

        # Accesos por hora (entradas de hoy) — datos reales para la gráfica, ventana operativa 6–22.
        por_hora = dict(
            RegistroAcceso.objects
            .filter(tipo_acceso=ENTRADA, hora_entrada__date=hoy)
            .annotate(h=ExtractHour("hora_entrada"))
            .values("h").annotate(c=Count("id")).values_list("h", "c")
        )
        accesos_por_hora = [{"hora": f"{h:02d}", "total": por_hora.get(h, 0)} for h in range(6, 23)]

        # Eventos en curso con su avance de ingreso hoy (recrea el widget EventosActuales del origen).
        eventos_actuales = []
        for ev in eventos_vigentes_qs.order_by("vigencia_inicio")[:8]:
            emp_ids = list(
                EmpleadoEventoProveedor.objects
                .filter(evento_proveedor__evento=ev).values_list("empleado_id", flat=True)
            )
            total = len(emp_ids)
            dentro = (
                RegistroAcceso.objects.filter(
                    evento=ev, tipo_acceso=ENTRADA, empleado_id__in=emp_ids, hora_entrada__date=hoy
                ).values("empleado").distinct().count()
            )
            eventos_actuales.append({
                "id": ev.id,
                "nombre": ev.nombre,
                "total_invitados": total,
                "total_ingresados": dentro,
                "porcentaje": round(dentro / total * 100) if total else 0,
            })

        return Response({
            "eventos_vigentes": eventos_vigentes_qs.count(),
            "invitados": invitados,
            "ingresados": ingresados,
            "pendientes_por_ingresar": max(invitados - ingresados, 0),
            "accesos_por_hora": accesos_por_hora,
            "eventos_actuales": eventos_actuales,
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
