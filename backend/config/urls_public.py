"""Control plane — schema 'public'.

F0.5 monta el webhook de Stripe (transiciona el estado del tenant). La gestión de tenants y la
creación de sesiones de checkout (acción del super-admin) se montan cuando exista la auth del
control plane; la lógica ya vive en ``apps.tenants.services`` (billing + stripe_gateway).
"""
from django.urls import path

from django.urls import include

from apps.tenants.admin_api import CrearCheckoutView, SuperAdminLoginView
from apps.tenants.webhooks import StripeWebhookView
from common.auth_api import MeView
from common.mfa_api import ActivarTOTPView, EnrolarTOTPView, VerificarMFAView

urlpatterns = [
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("", include("apps.dispositivos.urls")),  # F6: API edge /api/v1/* (HMAC)
    # Control plane (super-admin)
    path("api/admin/login/", SuperAdminLoginView.as_view(), name="admin-login"),
    path("api/admin/me/", MeView.as_view(), name="admin-me"),
    path("api/admin/mfa/totp/enrolar/", EnrolarTOTPView.as_view(), name="admin-mfa-enrolar"),
    path("api/admin/mfa/totp/activar/", ActivarTOTPView.as_view(), name="admin-mfa-activar"),
    path("api/admin/mfa/verificar/", VerificarMFAView.as_view(), name="admin-mfa-verificar"),
    path("api/admin/tenants/<int:tenant_id>/checkout/", CrearCheckoutView.as_view(),
         name="admin-checkout"),
]
