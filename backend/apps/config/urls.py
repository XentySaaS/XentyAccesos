"""Rutas de configuración, auditoría y reportes."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BitacoraAccesoViewSet,
    CalendarioView,
    DashboardView,
    ExportarAccesosView,
    HistorialCambioViewSet,
    OpcionViewSet,
    RetencionAuditoriaView,
)

router = DefaultRouter()
router.register("opciones", OpcionViewSet)
router.register("historial", HistorialCambioViewSet)
router.register("accesos-sistema", BitacoraAccesoViewSet)

urlpatterns = [
    path("config/retencion/", RetencionAuditoriaView.as_view(), name="retencion-auditoria"),
    path("reportes/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("reportes/calendario/", CalendarioView.as_view(), name="calendario"),
    path("reportes/accesos.xlsx", ExportarAccesosView.as_view(), name="exportar-accesos"),
    *router.urls,
]
