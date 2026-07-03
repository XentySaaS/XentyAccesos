"""Rutas REST de cumplimiento 69-B."""

from django.urls import path
from rest_framework.routers import DefaultRouter

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

urlpatterns = [
    path(
        "cumplimiento/validar/<int:proveedor_id>/",
        ValidarProveedorView.as_view(),
        name="cumplimiento-validar",
    ),
    path("cumplimiento/revalidar/", RevalidarView.as_view(), name="cumplimiento-revalidar"),
    path("cumplimiento/resumen/", ResumenView.as_view(), name="cumplimiento-resumen"),
    *router.urls,
]
