"""Rutas REST del módulo de documentos."""

from rest_framework.routers import DefaultRouter

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

urlpatterns = router.urls
