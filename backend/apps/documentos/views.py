"""ViewSets de documentos: catálogo (admin/acceso) + documentos de empleado + verificación."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.config.services import AuditViewSetMixin
from common.permissions import (
    PERMISOS_BASE,
    ContextoAcceso,
    RequiereModulo,
    RequiereRol,
)

from .models import DocumentoEmpleado, GrupoDocumentos, Protocolo, TipoDocumento
from .serializers import (
    DocumentoEmpleadoSerializer,
    GrupoDocumentosSerializer,
    ProtocoloSerializer,
    TipoDocumentoSerializer,
)
from .services import notificar_aprobacion, notificar_rechazo

_CATALOGO_PERMS = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("documentos"), RequiereRol("administrador"),
]


class GrupoDocumentosViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = GrupoDocumentos.objects.all().order_by("id")
    serializer_class = GrupoDocumentosSerializer
    permission_classes = _CATALOGO_PERMS
    filterset_fields = ["activo"]


class TipoDocumentoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = TipoDocumento.objects.all().order_by("id")
    serializer_class = TipoDocumentoSerializer
    filterset_fields = ["grupo", "activo"]

    def get_permissions(self):
        # Proveedores necesitan leer los tipos al subir documentos de sus empleados.
        if self.action in ("list", "retrieve"):
            return [*PERMISOS_BASE()]
        return list(_CATALOGO_PERMS)


class ProtocoloViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Protocolo.objects.all().order_by("id")
    serializer_class = ProtocoloSerializer
    permission_classes = _CATALOGO_PERMS
    filterset_fields = ["estado"]


class DocumentoEmpleadoViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoEmpleadoSerializer
    permission_classes = [*PERMISOS_BASE(), RequiereModulo("documentos")]
    filterset_fields = ["empleado", "estado", "tipo_documento"]

    def _ctx(self):
        return (self.request.auth or {}).get("ctx")

    def get_queryset(self):
        qs = DocumentoEmpleado.objects.all().order_by("-creado")
        if self._ctx() == "proveedores":
            return qs.filter(empleado__proveedor__proveedor_id=self.request.user.proveedor_id)
        return qs

    def perform_create(self, serializer):
        if self._ctx() != "proveedores":
            raise PermissionDenied("Solo el proveedor sube documentos.")
        empleado = serializer.validated_data["empleado"]
        if empleado.proveedor.proveedor_id != self.request.user.proveedor_id:
            raise ValidationError({"empleado": "No pertenece a tu empresa."})
        serializer.save()

    def _exige_verificador(self):
        if self._ctx() != "acceso" or self.request.user.rol not in ("verificador", "administrador"):
            raise PermissionDenied("Requiere rol verificador o administrador.")

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Descarga autenticada del archivo. El queryset ya filtra por pertenencia."""
        import mimetypes
        from django.http import FileResponse

        doc = self.get_object()
        if not doc.archivo:
            return Response({"detail": "Sin archivo."}, status=status.HTTP_404_NOT_FOUND)
        try:
            f = doc.archivo.open("rb")
        except (FileNotFoundError, OSError):
            return Response({"detail": "Archivo no encontrado en disco."}, status=status.HTTP_404_NOT_FOUND)
        content_type, _ = mimetypes.guess_type(doc.archivo.name)
        return FileResponse(f, content_type=content_type or "application/octet-stream")

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        self._exige_verificador()
        doc = self.get_object()
        doc.estado = DocumentoEmpleado.Estado.VERIFICADO
        doc.motivo_rechazo = None
        doc.save(update_fields=["estado", "motivo_rechazo"])
        # Propaga checkdocs: una asignación pendiente puede pasar a "cumple" al validar este doc.
        from apps.eventos.services import recalcular_status_asignaciones
        recalcular_status_asignaciones(doc.empleado)
        notificar_aprobacion(doc)
        return Response({"estado": doc.estado})

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        self._exige_verificador()
        doc = self.get_object()
        doc.estado = DocumentoEmpleado.Estado.RECHAZADO
        doc.motivo_rechazo = request.data.get("motivo", "")
        doc.save(update_fields=["estado", "motivo_rechazo"])
        # Al rechazar, una asignación que dependía de este doc deja de cumplir.
        from apps.eventos.services import recalcular_status_asignaciones
        recalcular_status_asignaciones(doc.empleado)
        notificar_rechazo(doc)
        return Response({"estado": doc.estado})
