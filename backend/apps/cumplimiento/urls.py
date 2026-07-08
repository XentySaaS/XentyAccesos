"""Rutas REST de cumplimiento 69-B y ARCO / LFPDPPP."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .arco_api import (
    BuscarTitularesView,
    CancelarTitularView,
    DocumentoLegalAdminView,
    DocumentoLegalPublicoView,
    ExportTitularView,
    SolicitudArcoViewSet,
)
from .views import (
    ResultadoViewSet,
    ResumenView,
    RevalidarView,
    SatEfoViewSet,
    ValidarProveedorView,
)

router = DefaultRouter()
router.register("cumplimiento/efos", SatEfoViewSet)
router.register("cumplimiento/resultados", ResultadoViewSet)
router.register("cumplimiento/arco/solicitudes", SolicitudArcoViewSet)

urlpatterns = [
    path(
        "cumplimiento/validar/<int:proveedor_id>/",
        ValidarProveedorView.as_view(),
        name="cumplimiento-validar",
    ),
    path("cumplimiento/revalidar/", RevalidarView.as_view(), name="cumplimiento-revalidar"),
    path("cumplimiento/resumen/", ResumenView.as_view(), name="cumplimiento-resumen"),
    # ARCO / LFPDPPP
    path("cumplimiento/arco/titulares/", BuscarTitularesView.as_view(), name="arco-titulares"),
    path(
        "cumplimiento/arco/export/<str:tipo>/<int:titular_id>/",
        ExportTitularView.as_view(),
        name="arco-export",
    ),
    path(
        "cumplimiento/arco/cancelar/<str:tipo>/<int:titular_id>/",
        CancelarTitularView.as_view(),
        name="arco-cancelar",
    ),
    path(
        "cumplimiento/arco/documentos/<str:tipo>/",
        DocumentoLegalAdminView.as_view(),
        name="arco-documento",
    ),
    # Documento legal público (sin auth), en contexto de tenant (Host)
    path(
        "privacidad/documento/<str:tipo>/",
        DocumentoLegalPublicoView.as_view(),
        name="privacidad-documento",
    ),
    *router.urls,
]
