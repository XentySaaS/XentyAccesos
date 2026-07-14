"""Rutas REST de mensajería."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .preferencia_api import PreferenciaMensajeriaView
from .sesion_api import WhatsAppQRView, WhatsAppSesionView
from .views import MensajeViewSet

router = DefaultRouter()
router.register("mensajes", MensajeViewSet)

urlpatterns = [
    path(
        "mensajeria/preferencia/",
        PreferenciaMensajeriaView.as_view(),
        name="mensajeria-preferencia",
    ),
    path("mensajeria/whatsapp/sesion/", WhatsAppSesionView.as_view(), name="mensajeria-wa-sesion"),
    path("mensajeria/whatsapp/qr/", WhatsAppQRView.as_view(), name="mensajeria-wa-qr"),
    *router.urls,
]
