"""Data plane — schema del tenant (por subdominio).

Autenticación de los dos contextos (F0.2):
  POST /api/auth/acceso/login/        -> Usuario (operación)
  POST /api/auth/proveedores/login/   -> CuentaProveedor (autoservicio)
  POST /api/auth/refresh/             -> rota el refresh (blacklist del anterior)
  POST /api/auth/logout/              -> invalida el refresh

F1+ monta las apps de negocio bajo /api/.
"""
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api import AccesoLoginView
from apps.proveedores.api import ProveedorLoginView
from common.auth_api import LogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/acceso/login/", AccesoLoginView.as_view(), name="acceso-login"),
    path("api/auth/proveedores/login/", ProveedorLoginView.as_view(), name="proveedores-login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    # path("api/", include("apps.<app>.urls")),  # F1+
]
