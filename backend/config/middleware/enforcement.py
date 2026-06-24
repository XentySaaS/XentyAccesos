"""Middlewares de enforcement del ciclo de vida del tenant (CLAUDE.md §6).

Orden (en ``settings.MIDDLEWARE``, tras ``TenantMainMiddleware`` que fija ``request.tenant``):
  RestringirAdminPorIP → EnforceMantenimiento → BloquearTenantsInactivos →
  [BloquearEmailNoVerificado (F0.4)] → BloquearTrialExpirado → EnforceModoSoloLectura →
  [EnforceMFAFullSession (F0.4)] → CorsMiddleware → estándar Django.

Todos respetan una **whitelist** de rutas (auth, billing, webhooks, health, schema) para que un
tenant suspendido/moroso SIEMPRE pueda autenticarse y pagar (REMEDIACION §A6).
"""
from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Rutas que jamás se bloquean: el cliente debe poder loguearse y pagar siempre.
WHITELIST_PREFIXES = (
    "/api/auth/",
    "/api/billing/",
    "/webhooks/",
    "/health",
    "/api/schema",
)


def _whitelisted(path: str) -> bool:
    return any(path.startswith(p) for p in WHITELIST_PREFIXES)


def _deny(detail: str, status: int) -> JsonResponse:
    return JsonResponse({"detail": detail}, status=status)


def _client_ip(request) -> str:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class RestringirAdminPorIP:
    """Restringe ``/admin/`` a una allowlist de IPs (``ADMIN_IP_ALLOWLIST``).

    Lista vacía ⇒ sin restricción (conveniencia de dev). Responde 403 si la IP no está permitida.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            allow = list(getattr(settings, "ADMIN_IP_ALLOWLIST", []) or [])
            if allow and _client_ip(request) not in allow:
                return _deny("Acceso a /admin/ no permitido desde esta IP.", 403)
        return self.get_response(request)


class EnforceMantenimiento:
    """Responde 503 si hay una ventana de mantenimiento activa (global, en ``public``)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _whitelisted(request.path) and self._en_mantenimiento():
            return _deny("Servicio en mantenimiento. Intenta más tarde.", 503)
        return self.get_response(request)

    @staticmethod
    def _en_mantenimiento() -> bool:
        from apps.tenants.models import VentanaMantenimiento

        ahora = timezone.now()
        with schema_context(get_public_schema_name()):
            return VentanaMantenimiento.objects.filter(
                activa=True, inicio__lte=ahora, fin__gte=ahora
            ).exists()


class _TenantStateMiddleware:
    """Base de los enforcement que dependen del estado del tenant.

    Corre solo en requests de un tenant real (no ``public``) y fuera de la whitelist.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)
        if (
            tenant is None
            or tenant.schema_name == get_public_schema_name()
            or _whitelisted(request.path)
        ):
            return self.get_response(request)
        bloqueo = self.evaluar(request, tenant)
        return bloqueo if bloqueo is not None else self.get_response(request)

    def evaluar(self, request, tenant):  # -> JsonResponse | None
        raise NotImplementedError


class BloquearTenantsInactivos(_TenantStateMiddleware):
    """Suspendido ⇒ 402 (debe regularizar el pago); cancelado ⇒ 403."""

    def evaluar(self, request, tenant):
        from apps.tenants.models import Tenant

        if tenant.estado == Tenant.Estado.CANCELADO:
            return _deny("La cuenta está cancelada.", 403)
        if tenant.estado == Tenant.Estado.SUSPENDIDO:
            return _deny("Cuenta suspendida. Regulariza tu pago para reactivarla.", 402)
        return None


class BloquearTrialExpirado(_TenantStateMiddleware):
    """Trial vencido ⇒ 402 con ruta de pago (la whitelist deja pasar billing)."""

    def evaluar(self, request, tenant):
        from apps.tenants.models import Tenant

        if (
            tenant.estado == Tenant.Estado.TRIAL
            and tenant.trial_ends_at is not None
            and tenant.trial_ends_at < timezone.now()
        ):
            return _deny("El periodo de prueba terminó. Suscríbete para continuar.", 402)
        return None


class EnforceModoSoloLectura(_TenantStateMiddleware):
    """Dunning/retención: en modo solo-lectura, los métodos de escritura responden 423."""

    def evaluar(self, request, tenant):
        if tenant.modo_solo_lectura and request.method not in SAFE_METHODS:
            return _deny("Cuenta en modo solo lectura.", 423)
        return None
