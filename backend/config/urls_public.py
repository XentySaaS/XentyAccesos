"""Control plane — schema 'public'.

F0.5 monta el webhook de Stripe (transiciona el estado del tenant). La gestión de tenants y la
creación de sesiones de checkout (acción del super-admin) se montan cuando exista la auth del
control plane; la lógica ya vive en ``apps.tenants.services`` (billing + stripe_gateway).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.ocr.views import ExtraerIneView
from apps.proveedores.views import OnboardingProveedorView
from apps.tenants.admin_api import (
    ConfiguracionConnectorView,
    CrearCheckoutView,
    PlanAdminViewSet,
    SignupView,
    SuperAdminLoginView,
    TenantAdminViewSet,
)
from apps.tenants.webhooks import StripeWebhookView
from common.auth_api import MeView
from common.health import LivenessView, ReadinessView
from common.mfa_api import ActivarTOTPView, EnrolarTOTPView, VerificarMFAView

router = DefaultRouter()
router.register("api/admin/tenants", TenantAdminViewSet, basename="admin-tenant")
router.register("api/admin/planes", PlanAdminViewSet, basename="admin-plan")

urlpatterns = [
    path("health/", LivenessView.as_view(), name="health"),
    path("health/ready/", ReadinessView.as_view(), name="health-ready"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("", include("apps.dispositivos.urls")),  # F6: API edge /api/v1/* (HMAC)
    # OCR público — usada en el onboarding antes de tener cuenta
    path("api/ocr/ine/", ExtraerIneView.as_view(), name="ocr-ine-public"),
    # Onboarding público de proveedores (accesible sin subdominio de tenant)
    path(
        "api/onboarding/proveedor/",
        OnboardingProveedorView.as_view(),
        name="onboarding-proveedor-public",
    ),
    # Alta pública self-service de tenants
    path("api/signup/", SignupView.as_view(), name="signup"),
    # Control plane (super-admin)
    path("api/admin/login/", SuperAdminLoginView.as_view(), name="admin-login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="admin-token-refresh"),
    path("api/admin/me/", MeView.as_view(), name="admin-me"),
    path("api/admin/mfa/totp/enrolar/", EnrolarTOTPView.as_view(), name="admin-mfa-enrolar"),
    path("api/admin/mfa/totp/activar/", ActivarTOTPView.as_view(), name="admin-mfa-activar"),
    path("api/admin/mfa/verificar/", VerificarMFAView.as_view(), name="admin-mfa-verificar"),
    path(
        "api/admin/tenants/<int:tenant_id>/checkout/",
        CrearCheckoutView.as_view(),
        name="admin-checkout",
    ),
    path(
        "api/admin/comunicaciones/",
        ConfiguracionConnectorView.as_view(),
        name="admin-comunicaciones",
    ),
    *router.urls,
]
