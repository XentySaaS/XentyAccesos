"""Rutas REST de eventos (router DRF)."""
from rest_framework.routers import DefaultRouter

from .views import EventoViewSet

router = DefaultRouter()
router.register("eventos", EventoViewSet, basename="evento")

urlpatterns = router.urls
