"""Rutas REST de mensajería."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .preferencia_api import PreferenciaMensajeriaView
from .views import MensajeViewSet

router = DefaultRouter()
router.register("mensajes", MensajeViewSet)

urlpatterns = [
    path(
        "mensajeria/preferencia/",
        PreferenciaMensajeriaView.as_view(),
        name="mensajeria-preferencia",
    ),
    *router.urls,
]
