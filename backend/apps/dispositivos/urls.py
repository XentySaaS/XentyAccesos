"""Rutas de la API edge ``/api/v1/*`` (se montan en el control plane / urls_public)."""
from django.urls import path

from .views import ComandoAckView, ComandosPullView, ValidarQREdgeView

urlpatterns = [
    path("api/v1/comandos/", ComandosPullView.as_view(), name="edge-comandos"),
    path("api/v1/comandos/<int:comando_id>/ack/", ComandoAckView.as_view(), name="edge-comando-ack"),
    path("api/v1/validar-qr/", ValidarQREdgeView.as_view(), name="edge-validar-qr"),
]
