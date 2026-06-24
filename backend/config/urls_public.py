"""Control plane — schema 'public'.

F0.5 monta el webhook de Stripe (transiciona el estado del tenant). La gestión de tenants y la
creación de sesiones de checkout (acción del super-admin) se montan cuando exista la auth del
control plane; la lógica ya vive en ``apps.tenants.services`` (billing + stripe_gateway).
"""
from django.urls import path

from django.urls import include

from apps.tenants.webhooks import StripeWebhookView

urlpatterns = [
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("", include("apps.dispositivos.urls")),  # F6: API edge /api/v1/* (HMAC)
]
