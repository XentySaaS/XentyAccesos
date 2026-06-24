"""ViewSets de documentos: catálogo (admin/acceso) + documentos de empleado + verificación."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from common.permissions import (
    PERMISOS_BASE,
    ContextoAcceso,
    RequiereModulo,
    RequiereRol,
)

from .models import DocumentoEmpleado, GrupoDocumentos, TipoDocumento
from .serializers import (
    DocumentoEmpleadoSerializer,
    GrupoDocumentosSerializer,
    TipoDocumentoSerializer,
)
from .services import notificar_rechazo

_CATALOGO_PERMS = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("documentos"), RequiereRol("administrador"),
]


class GrupoDocumentosViewSet(viewsets.ModelViewSet):
    queryset = GrupoDocumentos.objects.all().order_by("id")
    serializer_class = GrupoDocumentosSerializer
    permission_classes = _CATALOGO_PERMS
    filterset_fields = ["activo"]


class TipoDocumentoViewSet(viewsets.ModelViewSet):
    queryset = TipoDocumento.objects.all().order_by("id")
    serializer_class = TipoDocumentoSerializer
    permission_classes = _CATALOGO_PERMS
    filterset_fields = ["grupo", "activo"]


class DocumentoEmpleadoViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoEmpleadoSerializer
    permission_classes = [*PERMISOS_BASE(), RequiereModulo("documentos")]
    filterset_fields = ["empleado", "estado", "tipo_documento"]

    def _ctx(self):
        return (self.request.auth or {}).get("ctx")

    def get_queryset(self):
        qs = DocumentoEmpleado.objects.all().order_by("-creado")
        if self._ctx() == "proveedores":
            # El proveedor solo ve documentos de empleados de SU empresa.
            return qs.filter(empleado__proveedor__proveedor_id=self.request.user.proveedor_id)
        return qs  # acceso (verificador/administrador): bandeja de verificación

    def perform_create(self, serializer):
        if self._ctx() != "proveedores":
            raise PermissionDenied("Solo el proveedor sube documentos.")
        empleado = serializer.validated_data["empleado"]
        # El empleado debe pertenecer a la empresa del actor.
        if empleado.proveedor.proveedor_id != self.request.user.proveedor_id:
            raise ValidationError({"empleado": "No pertenece a tu empresa."})
        serializer.save()

    def _exige_verificador(self):
        if self._ctx() != "acceso" or self.request.user.rol not in ("verificador", "administrador"):
            raise PermissionDenied("Requiere rol verificador o administrador.")

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        self._exige_verificador()
        doc = self.get_object()
        doc.estado = DocumentoEmpleado.Estado.VERIFICADO
        doc.motivo_rechazo = None
        doc.save(update_fields=["estado", "motivo_rechazo"])
        return Response({"estado": doc.estado})

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        self._exige_verificador()
        doc = self.get_object()
        doc.estado = DocumentoEmpleado.Estado.RECHAZADO
        doc.motivo_rechazo = request.data.get("motivo", "")
        doc.save(update_fields=["estado", "motivo_rechazo"])
        notificar_rechazo(doc)
        return Response({"estado": doc.estado})
