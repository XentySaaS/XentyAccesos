"""Data plane — schema del tenant (por subdominio).

Autenticación de los dos contextos (F0.2):
  POST /api/auth/acceso/login/        -> Usuario (operación)
  POST /api/auth/proveedores/login/   -> CuentaProveedor (autoservicio)
  POST /api/auth/<ctx>/password/solicitar/  -> envía enlace de restablecimiento (self-service)
  POST /api/auth/<ctx>/password/confirmar/  -> fija la nueva contraseña con el token del enlace
  POST /api/auth/refresh/             -> rota el refresh (blacklist del anterior)
  POST /api/auth/logout/              -> invalida el refresh
  POST /api/auth/mfa/totp/enrolar/    -> genera secreto + QR (sesión completa)
  POST /api/auth/mfa/totp/activar/    -> verifica 1er código y activa MFA
  POST /api/auth/mfa/verificar/       -> completa la sesión MFA (token pendiente)

F1+ monta las apps de negocio bajo /api/.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api import (
    AccesoConfirmarResetView,
    AccesoLoginView,
    AccesoSolicitarResetView,
)
from apps.ocr.views import ExtraerIneView
from apps.proveedores.api import (
    ProveedorConfirmarResetView,
    ProveedorLoginView,
    ProveedorSolicitarResetView,
)
from apps.proveedores.views import DocumentoOnboardingView, OnboardingProveedorView
from apps.soporte.api import (
    ConfiguracionMesaView,
    EnviarDiagnosticoView,
    ProbarConexionView,
    SaludConfiguracionView,
)
from common.auth_api import LogoutView, MeView
from common.email_verify import VerificarEmailView
from common.health import LivenessView, ReadinessView
from common.mfa_api import (
    ActivarTOTPView,
    DesactivarTOTPView,
    EnrolarTOTPView,
    VerificarMFAView,
)
from common.webauthn_api import (
    LoginOpcionesView as WALoginOpcionesView,
)
from common.webauthn_api import (
    LoginVerificarView as WALoginVerificarView,
)
from common.webauthn_api import (
    RegistroOpcionesView as WARegistroOpcionesView,
)
from common.webauthn_api import (
    RegistroVerificarView as WARegistroVerificarView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", LivenessView.as_view(), name="health"),
    path("health/ready/", ReadinessView.as_view(), name="health-ready"),
    path("api/auth/acceso/login/", AccesoLoginView.as_view(), name="acceso-login"),
    path("api/auth/proveedores/login/", ProveedorLoginView.as_view(), name="proveedores-login"),
    path(
        "api/auth/acceso/password/solicitar/",
        AccesoSolicitarResetView.as_view(),
        name="acceso-password-solicitar",
    ),
    path(
        "api/auth/acceso/password/confirmar/",
        AccesoConfirmarResetView.as_view(),
        name="acceso-password-confirmar",
    ),
    path(
        "api/auth/proveedores/password/solicitar/",
        ProveedorSolicitarResetView.as_view(),
        name="proveedores-password-solicitar",
    ),
    path(
        "api/auth/proveedores/password/confirmar/",
        ProveedorConfirmarResetView.as_view(),
        name="proveedores-password-confirmar",
    ),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/mfa/totp/enrolar/", EnrolarTOTPView.as_view(), name="mfa-totp-enrolar"),
    path("api/auth/mfa/totp/activar/", ActivarTOTPView.as_view(), name="mfa-totp-activar"),
    path(
        "api/auth/mfa/totp/desactivar/",
        DesactivarTOTPView.as_view(),
        name="mfa-totp-desactivar",
    ),
    path("api/auth/mfa/verificar/", VerificarMFAView.as_view(), name="mfa-verificar"),
    path(
        "api/auth/mfa/webauthn/registro/opciones/",
        WARegistroOpcionesView.as_view(),
        name="mfa-wa-reg-opciones",
    ),
    path(
        "api/auth/mfa/webauthn/registro/verificar/",
        WARegistroVerificarView.as_view(),
        name="mfa-wa-reg-verificar",
    ),
    path(
        "api/auth/mfa/webauthn/login/opciones/",
        WALoginOpcionesView.as_view(),
        name="mfa-wa-login-opciones",
    ),
    path(
        "api/auth/mfa/webauthn/login/verificar/",
        WALoginVerificarView.as_view(),
        name="mfa-wa-login-verificar",
    ),
    path("api/auth/verificar-email/", VerificarEmailView.as_view(), name="verificar-email"),
    path("api/soporte/salud/", SaludConfiguracionView.as_view(), name="soporte-salud"),
    path("api/soporte/configuracion/", ConfiguracionMesaView.as_view(), name="soporte-config"),
    path("api/soporte/probar-conexion/", ProbarConexionView.as_view(), name="soporte-probar"),
    path("api/soporte/enviar-diagnostico/", EnviarDiagnosticoView.as_view(), name="soporte-diag"),
    path("api/ocr/ine/", ExtraerIneView.as_view(), name="ocr-ine"),
    path(
        "api/onboarding/proveedor/", OnboardingProveedorView.as_view(), name="onboarding-proveedor"
    ),
    path(
        "api/onboarding/documento/",
        DocumentoOnboardingView.as_view(),
        name="onboarding-documento",
    ),
    path("api/", include("apps.accounts.urls")),  # F1: gestión de usuarios del tenant
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
    path("api/", include("apps.config.urls")),  # F8: configuración, auditoría y reportes
]

if settings.DEBUG:
    # En dev servimos /media SOLO para archivos no sensibles (p. ej. fotos). Los directorios con
    # PII/documentos (INE, REPSE, SUA, docs de empleado) NO se exponen aquí: se descargan por
    # acciones autenticadas con policy de pertenencia (apps.documentos, apps.proveedores).
    # REMEDIACION §C5. En prod (DEBUG=False) /media no lo sirve Django en absoluto.
    from django.http import Http404
    from django.views.static import serve as _serve

    _MEDIA_PRIVADO = ("/ine/", "/repse/", "/sua/", "/documentos/")

    def _media_dev(request, path):
        if any(seg in ("/" + path.lower()) for seg in _MEDIA_PRIVADO):
            raise Http404("Archivo privado: usa el endpoint autenticado de descarga.")
        return _serve(request, path, document_root=settings.MEDIA_ROOT)

    urlpatterns += [re_path(r"^media/(?P<path>.*)$", _media_dev)]
