"""Rutas REST de la topología de recintos (router DRF)."""
from rest_framework.routers import DefaultRouter

from .views import (
    AccesoViewSet,
    AreaAutorizadaViewSet,
    EntradaViewSet,
    ProtocoloViewSet,
    RecintoViewSet,
    UbicacionViewSet,
    ZonaViewSet,
)

router = DefaultRouter()
router.register("recintos", RecintoViewSet)
router.register("zonas", ZonaViewSet)
router.register("accesos", AccesoViewSet)
router.register("ubicaciones", UbicacionViewSet)
router.register("entradas", EntradaViewSet)
router.register("areas-autorizadas", AreaAutorizadaViewSet)
router.register("protocolos", ProtocoloViewSet)

urlpatterns = router.urls
