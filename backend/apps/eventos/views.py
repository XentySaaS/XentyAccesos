"""ViewSet de Evento: CRUD, máquina de estados (acciones) y asignación de verificadores."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Usuario
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import Evento, VerificadorEvento
from .serializers import EventoSerializer


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
