"""Rutas REST de sanciones."""

from rest_framework.routers import DefaultRouter

from .views import SancionViewSet

router = DefaultRouter()
router.register("sanciones", SancionViewSet)

urlpatterns = router.urls
