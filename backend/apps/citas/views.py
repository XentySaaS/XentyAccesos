"""ViewSets de citas: Cita (con reglas de borrado), Contacto y AsistenteCita."""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import AsistenteCita, Cita, Contacto, EmpleadoCita
from .serializers import AsistenteCitaSerializer, CitaSerializer, ContactoSerializer

_ROLES = ("administrador", "editor", "recepcion", "guardia")
_PERMS = [*PERMISOS_BASE(), ContextoAcceso, RequiereModulo("citas"), RequiereRol(*_ROLES)]


class ContactoViewSet(viewsets.ModelViewSet):
    queryset = Contacto.objects.all().order_by("id")
    serializer_class = ContactoSerializer
    permission_classes = _PERMS
    search_fields = ["nombre", "email"]


class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all().order_by("-id")
    serializer_class = CitaSerializer
    permission_classes = _PERMS
    filterset_fields = ["tipo", "tipo_cita", "estado", "recinto", "proveedor"]

    def perform_create(self, serializer):
        serializer.save(creado_por_usuario=self.request.user)

    def perform_destroy(self, instance):
        # No eliminable: tipo proveedor con empleados, o tipo directa con asistentes (SAR_FUNC §7.1).
        if instance.tipo == Cita.Tipo.PROVEEDOR and EmpleadoCita.objects.filter(cita=instance).exists():
            raise PermissionDenied("La cita de proveedor tiene empleados asignados.")
        if instance.tipo == Cita.Tipo.DIRECTA and instance.asistentes.exists():
            raise PermissionDenied("La cita directa tiene asistentes registrados.")
        instance.delete()


class AsistenteCitaViewSet(viewsets.ModelViewSet):
    queryset = AsistenteCita.objects.all().order_by("id")
    serializer_class = AsistenteCitaSerializer
    permission_classes = _PERMS
    filterset_fields = ["cita", "tipo", "estado"]
