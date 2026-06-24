"""Rutas REST de proveedores: catálogo (router) + onboarding público."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import OnboardingProveedorView, ProveedorViewSet

router = DefaultRouter()
router.register("proveedores", ProveedorViewSet)

urlpatterns = [
    path("onboarding/proveedor/", OnboardingProveedorView.as_view(), name="onboarding-proveedor"),
    *router.urls,
]
