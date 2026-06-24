"""Rutas REST de acceso físico."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EscanearView, RegistroAccesoViewSet

router = DefaultRouter()
router.register("acceso/registros", RegistroAccesoViewSet, basename="registro-acceso")

urlpatterns = [
    path("acceso/escanear/", EscanearView.as_view(), name="acceso-escanear"),
    *router.urls,
]
