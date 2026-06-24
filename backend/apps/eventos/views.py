"""ViewSet de Evento: CRUD, máquina de estados (acciones) y asignación de verificadores."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.documentos.services import cumple_requisitos
from apps.empleados.models import Empleado
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import (
    CajonParking,
    EmpleadoEventoProveedor,
    Evento,
    EventoGrupoDocumentos,
    EventoProveedor,
    VerificadorEvento,
)
from .serializers import EventoProveedorSerializer, EventoSerializer


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
            for g in grupos
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
        # F3.2/F7: al cancelar se dispara WhatsApp a los proveedores del evento.
        return self._transicionar(self.get_object(), Evento.Estado.CANCELADO)

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

    def perform_create(self, serializer):
        self._exige_operacion()
        ep = serializer.save()
        # Crea los cajones de parking declarados (su uuid va en el QR de estacionamiento, F5).
        if ep.requiere_parking and ep.cajones_parking > 0:
            CajonParking.objects.bulk_create(
                [CajonParking(evento_proveedor=ep) for _ in range(ep.cajones_parking)]
            )

    def perform_update(self, serializer):
        self._exige_operacion()
        serializer.save()

    def perform_destroy(self, instance):
        self._exige_operacion()
        instance.delete()

    @action(detail=True, methods=["post"], url_path="asignar-empleados")
    def asignar_empleados(self, request, pk=None):
        """Asignación masiva (proveedor): valida límite y exige checkdocs; fija statusdocs=CUMPLE."""
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

        no_cumplen = [e.id for e in empleados if not cumple_requisitos(e, requisitos)]
        if no_cumplen:
            return Response(
                {"detail": "Hay empleados sin los documentos requeridos verificados.",
                 "empleados": no_cumplen},
                status=status.HTTP_400_BAD_REQUEST,
            )

        creados = 0
        for e in empleados:
            _, creado = EmpleadoEventoProveedor.objects.get_or_create(
                evento_proveedor=ep, empleado=e,
                defaults={"statusdocs": EmpleadoEventoProveedor.StatusDocs.CUMPLE},
            )
            creados += int(creado)
        # F5: aquí se dispara la emisión del gafete QR.
        return Response({"asignados": creados})
