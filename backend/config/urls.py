"""Data plane — schema del tenant (por subdominio).

Autenticación de los dos contextos (F0.2):
  POST /api/auth/acceso/login/        -> Usuario (operación)
  POST /api/auth/proveedores/login/   -> CuentaProveedor (autoservicio)
  POST /api/auth/refresh/             -> rota el refresh (blacklist del anterior)
  POST /api/auth/logout/              -> invalida el refresh
  POST /api/auth/mfa/totp/enrolar/    -> genera secreto + QR (sesión completa)
  POST /api/auth/mfa/totp/activar/    -> verifica 1er código y activa MFA
  POST /api/auth/mfa/verificar/       -> completa la sesión MFA (token pendiente)

F1+ monta las apps de negocio bajo /api/.
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api import AccesoLoginView
from apps.proveedores.api import ProveedorLoginView
from apps.soporte.api import SaludConfiguracionView
from common.auth_api import LogoutView, MeView
from common.mfa_api import ActivarTOTPView, EnrolarTOTPView, VerificarMFAView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/acceso/login/", AccesoLoginView.as_view(), name="acceso-login"),
    path("api/auth/proveedores/login/", ProveedorLoginView.as_view(), name="proveedores-login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/mfa/totp/enrolar/", EnrolarTOTPView.as_view(), name="mfa-totp-enrolar"),
    path("api/auth/mfa/totp/activar/", ActivarTOTPView.as_view(), name="mfa-totp-activar"),
    path("api/auth/mfa/verificar/", VerificarMFAView.as_view(), name="mfa-verificar"),
    path("api/soporte/salud/", SaludConfiguracionView.as_view(), name="soporte-salud"),
    path("api/", include("apps.recintos.urls")),  # F1: topología de recintos
    path("api/", include("apps.proveedores.urls")),  # F1: catálogo + onboarding de proveedores
    path("api/", include("apps.empleados.urls")),  # F1: plantilla de empleados del proveedor
    path("api/", include("apps.documentos.urls")),  # F2: catálogo documental + verificación
    path("api/", include("apps.eventos.urls")),  # F3: eventos
    path("api/", include("apps.citas.urls")),  # F4: citas
    path("api/", include("apps.acceso.urls")),  # F5: acceso físico (escáner + bitácora)
    path("api/", include("apps.sanciones.urls")),  # F5: sanciones
    path("api/", include("apps.mensajeria.urls")),  # F7: mensajería WhatsApp
    path("api/", include("apps.cumplimiento.urls")),  # F7: cumplimiento SAT 69-B
]
