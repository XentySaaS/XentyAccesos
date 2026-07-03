"""Rutas REST de eventos (router DRF)."""

from rest_framework.routers import DefaultRouter

from .views import EventoProveedorViewSet, EventoViewSet

router = DefaultRouter()
router.register("eventos", EventoViewSet, basename="evento")
router.register("evento-proveedores", EventoProveedorViewSet, basename="evento-proveedor")

urlpatterns = router.urls
