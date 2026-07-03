"""Rutas REST de mensajería."""

from rest_framework.routers import DefaultRouter

from .views import MensajeViewSet

router = DefaultRouter()
router.register("mensajes", MensajeViewSet)

urlpatterns = router.urls
