"""Rutas REST de citas."""
from rest_framework.routers import DefaultRouter

from .views import AsistenteCitaViewSet, CitaViewSet, ContactoViewSet

router = DefaultRouter()
router.register("citas", CitaViewSet)
router.register("contactos", ContactoViewSet)
router.register("asistentes-cita", AsistenteCitaViewSet)

urlpatterns = router.urls
