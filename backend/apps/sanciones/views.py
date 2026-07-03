"""ViewSet de Sanciones (severidad/penalidad solo Administrador).

Además del CRUD expone apoyos para el alta de una amonestación desde operación (como el
WarningResource del origen): búsqueda de empleados por nombre (autocomplete, no un select con
todos), lista ligera de eventos y resolución del QR del gafete para identificar al empleado.
"""

from __future__ import annotations

from django.db import connection
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.config.services import AuditViewSetMixin
from common.permissions import (
    PERMISOS_BASE,
    ContextoAcceso,
    RequiereModulo,
    RequierePermisoPersonalizado,
    RequiereRol,
)

from .models import Sancion
from .serializers import SancionSerializer


def _empresa_de(empleado) -> str:
    """Nombre de la empresa proveedora del empleado (para desambiguar homónimos)."""
    try:
        cuenta = empleado.proveedor
        return cuenta.proveedor.nombre if getattr(cuenta, "proveedor_id", None) else ""
    except Exception:  # noqa: BLE001
        return ""


class SancionViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Sancion.objects.all().order_by("-creado")
    serializer_class = SancionSerializer
    permission_classes = [
        *PERMISOS_BASE(),
        ContextoAcceso,
        RequiereModulo("sanciones"),
        RequiereRol("administrador", "guardia", "usuario"),
        RequierePermisoPersonalizado("sanciones"),
    ]
    filterset_fields = ["empleado", "penalidad", "severidad"]

    @action(detail=False, methods=["get"], url_path="buscar-empleados")
    def buscar_empleados(self, request):
        """Empleados asignados a un evento (?evento=), opcionalmente filtrados por nombre (?q=).

        El flujo es evento→empleado: no todos los empleados asisten a un evento, así que la
        búsqueda se acota a los asignados a ese evento. Sin ``evento`` cae a búsqueda general por
        nombre (mínimo 2 caracteres) como respaldo.
        """
        from apps.empleados.models import Empleado
        from apps.eventos.models import EmpleadoEventoProveedor

        q = (request.query_params.get("q") or "").strip()
        evento_id = request.query_params.get("evento")

        empleados = Empleado.objects.filter(estado=Empleado.Estado.ACTIVO).select_related(
            "proveedor"
        )
        if evento_id:
            ids = EmpleadoEventoProveedor.objects.filter(
                evento_proveedor__evento_id=evento_id
            ).values_list("empleado_id", flat=True)
            empleados = empleados.filter(id__in=list(ids))
            if q:
                empleados = empleados.filter(nombre__icontains=q)
        else:
            if len(q) < 2:
                return Response([])
            empleados = empleados.filter(nombre__icontains=q)

        return Response(
            [
                {"id": e.id, "nombre": e.nombre, "empresa": _empresa_de(e)}
                for e in empleados.order_by("nombre")[:50]
            ]
        )

    @action(detail=False, methods=["get"])
    def eventos(self, request):
        """Lista ligera de eventos ACTIVOS (programado / en curso) para el campo 'evento'."""
        from apps.eventos.models import Evento

        qs = Evento.objects.filter(
            estado__in=[Evento.Estado.PROGRAMADO, Evento.Estado.EN_CURSO]
        ).order_by("-vigencia_inicio")[:100]
        return Response([{"id": ev.id, "nombre": ev.nombre, "estado": ev.estado} for ev in qs])

    @action(detail=False, methods=["post"], url_path="resolver-qr")
    def resolver_qr(self, request):
        """Identifica al empleado (y su evento) a partir del QR de su gafete, para amonestarlo.

        Reemplaza el 'Escanear QR' del origen: en vez de leer un id crudo, verifica el token
        cifrado (Fernet, con tenant) y resuelve el empleado del gafete de evento o de cita.
        """
        from apps.gafetes.services import TIPO_CITA, TIPO_EVENTO, QRInvalido, verificar_qr

        try:
            data = verificar_qr(request.data.get("qr", ""), tenant=connection.schema_name)
        except QRInvalido as e:
            return Response({"detail": str(e)}, status=400)

        tipo, rid = data.get("tipo"), data.get("id")
        empleado = evento = None

        if tipo == TIPO_EVENTO:
            from apps.eventos.models import EmpleadoEventoProveedor

            eep = (
                EmpleadoEventoProveedor.objects.select_related(
                    "empleado", "evento_proveedor__evento"
                )
                .filter(id=rid)
                .first()
            )
            if eep:
                empleado = eep.empleado
                evento = eep.evento_proveedor.evento
        elif tipo == TIPO_CITA:
            from apps.citas.models import AsistenteCita

            asis = AsistenteCita.objects.filter(id=rid).first()
            # El asistente solo es sancionable si es un Empleado del catálogo.
            if asis and asis.tipo == AsistenteCita.Tipo.EMPLEADO and asis.persona is not None:
                empleado = asis.persona

        if empleado is None:
            return Response(
                {"detail": "El QR no corresponde a un empleado sancionable."}, status=404
            )
        return Response(
            {
                "empleado_id": empleado.id,
                "empleado_nombre": empleado.nombre,
                "empresa": _empresa_de(empleado),
                "evento_id": evento.id if evento else None,
                "evento_nombre": evento.nombre if evento else None,
            }
        )
