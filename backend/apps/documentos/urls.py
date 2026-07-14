"""Rutas REST del módulo de documentos."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .verificacion_api import (
    EmpleadosVerificacionView,
    EventosVerificacionView,
    ProveedoresVerificacionView,
)
from .views import (
    DocumentoEmpleadoViewSet,
    GrupoDocumentosViewSet,
    ProtocoloViewSet,
    TipoDocumentoViewSet,
)

router = DefaultRouter()
router.register("grupos-documentos", GrupoDocumentosViewSet)
router.register("tipos-documento", TipoDocumentoViewSet)
router.register("protocolos", ProtocoloViewSet)
router.register("documentos-empleado", DocumentoEmpleadoViewSet, basename="documento-empleado")

urlpatterns = [
    # Workspace de verificación (drill-down): proveedores → empleados → documentos.
    path(
        "verificacion/proveedores/", ProveedoresVerificacionView.as_view(), name="verif-proveedores"
    ),
    path("verificacion/empleados/", EmpleadosVerificacionView.as_view(), name="verif-empleados"),
    path("verificacion/eventos/", EventosVerificacionView.as_view(), name="verif-eventos"),
    *router.urls,
]
