"""ViewSet de Evento: CRUD, máquina de estados (acciones), verificadores, invitaciones y gafetes."""
from __future__ import annotations

from datetime import datetime, time as dtime, timezone as dtz

from django.db import connection
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.documentos.services import cumple_requisitos
from apps.empleados.models import Empleado
from apps.gafetes.services import TIPO_EVENTO, TIPO_PARKING, componer_gafete, emitir_qr
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from . import services as noti
from .models import (
    CajonParking,
    EmpleadoEventoProveedor,
    Evento,
    EventoGrupoDocumentos,
    EventoProveedor,
    VerificadorEvento,
)
from .serializers import EventoProveedorSerializer, EventoSerializer


def _tenant_nombre(request) -> str:
    return getattr(getattr(request, "tenant", None), "nombre", connection.schema_name)


def _base_url(request) -> str:
    return f"{request.scheme}://{request.get_host()}"


class EventoViewSet(viewsets.ModelViewSet):
    serializer_class = EventoSerializer
    permission_classes = [
        *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("eventos"),
        RequiereRol("administrador", "editor"),
    ]
    filterset_fields = ["estado", "recinto"]

    def get_queryset(self):
        qs = Evento.objects.all().order_by("-id")
        # Un usuario NO administrador solo ve los eventos que él creó (SAR_FUNC §6.1).
        if self.request.user.rol != Usuario.Rol.ADMINISTRADOR:
            qs = qs.filter(creado_por=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    def perform_destroy(self, instance):
        # No eliminable si tiene proveedores o empleados asignados (SAR_FUNC §6.1).
        if EventoProveedor.objects.filter(evento=instance).exists():
            raise PermissionDenied("No se puede eliminar un evento con proveedores asignados.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="requisitos-documentos")
    def requisitos_documentos(self, request, pk=None):
        """Define los grupos de documentos requeridos del evento (con su type_validation)."""
        evento = self.get_object()
        grupos = request.data.get("grupos", [])  # [{"grupo": id, "type_validation": 0|1}]
        EventoGrupoDocumentos.objects.filter(evento=evento).delete()
        EventoGrupoDocumentos.objects.bulk_create([
            EventoGrupoDocumentos(
                evento=evento, grupo_id=g["grupo"], type_validation=g.get("type_validation", 0)
            )
            for g in grupos if g.get("grupo")
        ])
        return Response({"requisitos": len(grupos)})

    def _transicionar(self, evento, nuevo):
        if not evento.puede_transicionar(nuevo):
            return Response(
                {"detail": f"Transición no permitida desde '{evento.estado}'."},
                status=status.HTTP_409_CONFLICT,
            )
        evento.estado = nuevo
        evento.save(update_fields=["estado"])
        return Response({"estado": evento.estado})

    @action(detail=True, methods=["post"])
    def iniciar(self, request, pk=None):
        return self._transicionar(self.get_object(), Evento.Estado.EN_CURSO)

    @action(detail=True, methods=["post"])
    def completar(self, request, pk=None):
        return self._transicionar(self.get_object(), Evento.Estado.COMPLETADO)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """Cancela el evento y notifica por WhatsApp/correo a los proveedores invitados."""
        evento = self.get_object()
        resp = self._transicionar(evento, Evento.Estado.CANCELADO)
        if resp.status_code == status.HTTP_200_OK:
            notificados = noti.notificar_evento_cancelado(evento, nombre_tenant=_tenant_nombre(request))
            resp.data["notificados"] = notificados
        return resp

    @action(detail=True, methods=["post"])
    def asignar_verificadores(self, request, pk=None):
        """Reemplaza el conjunto de verificadores del evento por los usuarios indicados."""
        evento = self.get_object()
        ids = request.data.get("usuarios", [])
        usuarios = Usuario.objects.filter(id__in=ids)
        VerificadorEvento.objects.filter(evento=evento).delete()
        VerificadorEvento.objects.bulk_create(
            [VerificadorEvento(evento=evento, usuario=u) for u in usuarios]
        )
        return Response({"verificadores": list(usuarios.values_list("id", flat=True))})


class EventoProveedorViewSet(viewsets.ModelViewSet):
    """Invitaciones de proveedores a un evento.

    CRUD lo opera el recinto (contexto acceso, admin/editor). La asignación masiva de empleados la
    hace el proveedor (contexto proveedores) sobre SUS invitaciones.
    """

    serializer_class = EventoProveedorSerializer
    permission_classes = [*PERMISOS_BASE(), RequiereModulo("eventos")]
    filterset_fields = ["evento", "proveedor"]

    def _ctx(self):
        return (self.request.auth or {}).get("ctx")

    def get_queryset(self):
        qs = EventoProveedor.objects.all().order_by("-id")
        if self._ctx() == "proveedores":
            return qs.filter(proveedor__cuentas=self.request.user)
        return qs

    def _exige_operacion(self):
        if self._ctx() != "acceso" or self.request.user.rol not in ("administrador", "editor"):
            raise PermissionDenied("Solo operación (admin/editor) gestiona invitaciones.")

    @staticmethod
    def _sync_cajones(ep: EventoProveedor) -> None:
        """Ajusta los cajones de parking para que coincidan con cajones_parking (crea/borra)."""
        objetivo = ep.cajones_parking if ep.requiere_parking else 0
        actuales = ep.cajones.count()
        if objetivo > actuales:
            CajonParking.objects.bulk_create(
                [CajonParking(evento_proveedor=ep) for _ in range(objetivo - actuales)]
            )
        elif objetivo < actuales:
            sobran = list(
                ep.cajones.order_by("-id").values_list("id", flat=True)[: actuales - objetivo]
            )
            CajonParking.objects.filter(id__in=sobran).delete()

    def perform_create(self, serializer):
        self._exige_operacion()
        ep = serializer.save()
        self._sync_cajones(ep)
        noti.notificar_invitacion(
            ep, nombre_tenant=_tenant_nombre(self.request), panel_url=_base_url(self.request)
        )

    def perform_update(self, serializer):
        self._exige_operacion()
        ep = serializer.save()
        self._sync_cajones(ep)

    def perform_destroy(self, instance):
        self._exige_operacion()
        noti.notificar_invitacion_cancelada(instance, nombre_tenant=_tenant_nombre(self.request))
        instance.delete()

    # ── Gafetes (QR cifrado + tarjeta compuesta) ─────────────────────────────
    @staticmethod
    def _exp_epoch(evento) -> float:
        """Fin de la vigencia del evento (fin del día) en epoch, para el ``exp`` del QR."""
        return datetime.combine(evento.vigencia_fin, dtime(23, 59, 59), tzinfo=dtz.utc).timestamp()

    def _lineas_evento(self, ep) -> list[str]:
        ev = ep.evento
        lineas = [ev.nombre]
        if ep.zona_id:
            lineas.append(f"Zona: {ep.zona.nombre}")
        if ep.acceso_id:
            lineas.append(f"Acceso: {ep.acceso.nombre}")
        fecha = ev.vigencia_inicio.strftime("%d/%m/%Y")
        if ev.hora_inicio:
            fecha += f" · {ev.hora_inicio.strftime('%H:%M')}"
        lineas.append(fecha)
        return lineas

    @action(detail=True, methods=["get"], url_path="gafete-empleado")
    def gafete_empleado(self, request, pk=None):
        """Gafete de acceso (QR) de un empleado asignado a esta invitación."""
        ep = self.get_object()
        asignacion = (
            EmpleadoEventoProveedor.objects
            .filter(evento_proveedor=ep, empleado_id=request.query_params.get("empleado"))
            .select_related("empleado").first()
        )
        if asignacion is None:
            return Response({"detail": "Empleado no asignado a esta invitación."}, status=404)
        empleado = asignacion.empleado
        token = emitir_qr(
            id=asignacion.id, tipo=TIPO_EVENTO, tenant=connection.schema_name,
            exp_epoch=self._exp_epoch(ep.evento),
        )
        foto = empleado.foto.read() if empleado.foto else None
        png = componer_gafete(
            token=token, titulo=empleado.nombre, recinto=ep.evento.recinto.nombre,
            lineas=self._lineas_evento(ep), foto_bytes=foto, empresa=_tenant_nombre(request),
        )
        return HttpResponse(png, content_type="image/png")

    @action(detail=True, methods=["get"], url_path="gafete-parking")
    def gafete_parking(self, request, pk=None):
        """Gafete de estacionamiento (QR) de un cajón de esta invitación."""
        ep = self.get_object()
        cajon = ep.cajones.filter(id=request.query_params.get("cajon")).first() or ep.cajones.first()
        if cajon is None:
            return Response({"detail": "Esta invitación no tiene cajones de parking."}, status=404)
        token = emitir_qr(
            id=cajon.id, tipo=TIPO_PARKING, tenant=connection.schema_name,
            exp_epoch=self._exp_epoch(ep.evento), contexto=str(cajon.uuid),
        )
        lineas = self._lineas_evento(ep)
        if ep.parking:
            lineas.append(f"Estacionamiento: {ep.parking}")
        png = componer_gafete(
            token=token, titulo=ep.proveedor.nombre, recinto=ep.evento.recinto.nombre,
            lineas=lineas, empresa=_tenant_nombre(request),
        )
        return HttpResponse(png, content_type="image/png")

    def _exige_proveedor_dueno(self, ep):
        if self._ctx() != "proveedores" or ep.proveedor_id != getattr(self.request.user, "proveedor_id", None):
            raise PermissionDenied("Solo el proveedor dueño de la invitación opera sus empleados.")

    @action(detail=True, methods=["get"])
    def requisitos(self, request, pk=None):
        """Grupos de documentos requeridos por el evento (con sus tipos), para mostrar al proveedor."""
        from apps.documentos.models import TipoDocumento

        ep = self.get_object()
        reqs = (
            EventoGrupoDocumentos.objects
            .filter(evento=ep.evento).select_related("grupo").order_by("id")
        )
        data = [{
            "grupo": r.grupo_id,
            "grupo_nombre": r.grupo.nombre,
            "type_validation": r.type_validation,
            "tipos": list(TipoDocumento.objects.filter(grupo_id=r.grupo_id, activo=True).values("id", "nombre")),
        } for r in reqs]
        return Response({"requisitos": data})

    @action(detail=True, methods=["get"])
    def candidatos(self, request, pk=None):
        """Empleados del proveedor con su elegibilidad para el evento (estado documental + asignado)."""
        ep = self.get_object()
        if self._ctx() == "proveedores":
            self._exige_proveedor_dueno(ep)

        reqs = list(
            EventoGrupoDocumentos.objects.filter(evento=ep.evento).select_related("grupo").order_by("id")
        )
        # Mapa empleado_id → statusdocs para saber si está asignado y con qué estado documental.
        asignaciones = {
            a.empleado_id: a.statusdocs
            for a in EmpleadoEventoProveedor.objects.filter(evento_proveedor=ep)
        }
        empleados = Empleado.objects.filter(
            proveedor__proveedor_id=ep.proveedor_id, estado=Empleado.Estado.ACTIVO
        ).order_by("nombre")

        out = []
        for e in empleados:
            cumple, detalle = noti.estado_documental(e, reqs)
            out.append({
                "id": e.id, "nombre": e.nombre,
                "asignado": e.id in asignaciones,
                "statusdocs": asignaciones.get(e.id),  # 0=pendiente, 1=cumple, None=no asignado
                "cumple": cumple, "detalle": detalle,
            })
        return Response({
            "empleados": out,
            "limite": ep.limite,
            "asignados_count": len(asignaciones),
            "requiere_documentos": bool(reqs),
        })

    @action(detail=True, methods=["post"], url_path="desasignar-empleados")
    def desasignar_empleados(self, request, pk=None):
        """Quita empleados de la invitación (lado proveedor)."""
        ep = self.get_object()
        self._exige_proveedor_dueno(ep)
        ids = request.data.get("empleados", [])
        qs = EmpleadoEventoProveedor.objects.filter(
            evento_proveedor=ep, empleado_id__in=ids
        ).select_related("empleado")
        quitados = [a.empleado for a in qs]
        borradas = qs.delete()[0]
        for emp in quitados:
            noti.notificar_desasignacion_empleado(emp, ep.evento, nombre_tenant=_tenant_nombre(request))
        return Response({"desasignados": borradas})

    @action(detail=True, methods=["post"], url_path="asignar-empleados")
    def asignar_empleados(self, request, pk=None):
        """Asignación (proveedor): si cumple docs → statusdocs=CUMPLE + notifica; si faltan → PENDIENTE.

        El empleado queda registrado aunque sus documentos no estén verificados todavía. Cuando el
        recinto apruebe los documentos, ``recalcular_status_asignaciones`` transitará el status a
        CUMPLE y enviará la notificación en ese momento.
        """
        ep = self.get_object()
        if self._ctx() != "proveedores" or ep.proveedor_id != getattr(request.user, "proveedor_id", None):
            raise PermissionDenied("Solo el proveedor dueño asigna empleados.")

        empleados = list(Empleado.objects.filter(
            id__in=request.data.get("empleados", []),
            proveedor__proveedor_id=request.user.proveedor_id,
        ))
        requisitos = list(
            EventoGrupoDocumentos.objects.filter(evento=ep.evento)
            .values_list("grupo_id", "type_validation")
        )

        actuales = EmpleadoEventoProveedor.objects.filter(evento_proveedor=ep).count()
        if ep.limite and actuales + len(empleados) > ep.limite:
            return Response(
                {"detail": f"Excede el límite de {ep.limite} personas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        creados = 0
        for e in empleados:
            cumple = cumple_requisitos(e, requisitos)
            nuevo_status = (
                EmpleadoEventoProveedor.StatusDocs.CUMPLE
                if (cumple or not requisitos)
                else EmpleadoEventoProveedor.StatusDocs.PENDIENTES
            )
            asignacion, creado = EmpleadoEventoProveedor.objects.get_or_create(
                evento_proveedor=ep, empleado=e,
                defaults={"statusdocs": nuevo_status},
            )
            if creado:
                creados += 1
                # Solo notifica al empleado cuando ya cumple con los documentos requeridos.
                if nuevo_status == EmpleadoEventoProveedor.StatusDocs.CUMPLE:
                    noti.notificar_asignacion_empleado(asignacion, nombre_tenant=_tenant_nombre(request))
        return Response({"asignados": creados})
