"""Rutas de gestión de usuarios del tenant."""
from rest_framework.routers import DefaultRouter

from .views import UsuarioViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet)

urlpatterns = router.urls
