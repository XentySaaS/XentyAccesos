"""Rutas de configuración, auditoría y reportes."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CalendarioView,
    DashboardView,
    ExportarAccesosView,
    HistorialCambioViewSet,
    OpcionViewSet,
)

router = DefaultRouter()
router.register("opciones", OpcionViewSet)
router.register("historial", HistorialCambioViewSet)

urlpatterns = [
    path("reportes/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("reportes/calendario/", CalendarioView.as_view(), name="calendario"),
    path("reportes/accesos.xlsx", ExportarAccesosView.as_view(), name="exportar-accesos"),
    *router.urls,
]
