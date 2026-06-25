"""Permission classes globales de enforcement por ACTOR (CLAUDE.md §6, slots 5 y 9).

Se aplican vía ``DEFAULT_PERMISSION_CLASSES``. A diferencia de los enforcement por tenant (que son
middleware sobre ``request.tenant``), estos dependen del actor autenticado y por eso viven en la
capa DRF, donde la autenticación JWT ya resolvió ``request.user`` / ``request.auth``.

Endpoints que deben quedar exentos (login, verificación MFA) fijan su propio ``permission_classes``.
"""
from __future__ import annotations

from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission, IsAuthenticated


class ModuloNoContratado(APIException):
    """HTTP 402: el módulo solicitado no está incluido en el plan del tenant."""

    status_code = 402
    default_detail = "Este módulo no está incluido en el plan contratado."
    default_code = "modulo_no_contratado"


def RequiereModulo(modulo: str):
    """Permission de módulo comercial: 402 si el plan del tenant no incluye ``modulo``.

    Uso: ``permission_classes = [RequiereModulo("eventos")]``. Lee ``request.tenant.plan.modulos``.
    """

    class _RequiereModulo(BasePermission):
        def has_permission(self, request, view):
            tenant = getattr(request, "tenant", None)
            plan = getattr(tenant, "plan", None) if tenant else None
            modulos = (getattr(plan, "modulos", None) or []) if plan else []
            if modulo in modulos:
                return True
            raise ModuloNoContratado()

    return _RequiereModulo


def RequiereRol(*roles: str):
    """Permission de rol primario: pasa solo si ``request.user.rol`` está en ``roles``.

    Uso: ``permission_classes = [RequiereRol("administrador", "editor")]``.
    """

    class _RequiereRol(BasePermission):
        message = "Tu rol no tiene permiso para esta acción."

        def has_permission(self, request, view):
            user = getattr(request, "user", None)
            return bool(user and user.is_authenticated and getattr(user, "rol", None) in roles)

    return _RequiereRol


class ContextoProveedores(BasePermission):
    """Solo actores del contexto *proveedores* (claim ``ctx="proveedores"``)."""

    message = "Disponible solo para cuentas de proveedor."

    def has_permission(self, request, view):
        return (request.auth or {}).get("ctx") == "proveedores"


class ContextoAcceso(BasePermission):
    """Solo actores del contexto *acceso* (operación del recinto)."""

    message = "Disponible solo para usuarios de operación."

    def has_permission(self, request, view):
        return (request.auth or {}).get("ctx") == "acceso"


class EsSuperAdmin(BasePermission):
    """Solo el super-admin del control plane (claim ``ctx="superadmin"``)."""

    message = "Disponible solo para el super-admin."

    def has_permission(self, request, view):
        return (request.auth or {}).get("ctx") == "superadmin"


class RequiereMembresia(BasePermission):
    """Pertenencia a nivel objeto: el proveedor solo accede a recursos de su propia empresa.

    Se refina en F1 (cuando ``CuentaProveedor.proveedor`` y los modelos de negocio existan). Si no
    hay relación de proveedor en juego, no restringe.
    """

    def has_object_permission(self, request, view, obj):
        actor_prov = getattr(request.user, "proveedor_id", None)
        obj_prov = getattr(obj, "proveedor_id", None)
        if actor_prov is None or obj_prov is None:
            return True
        return actor_prov == obj_prov


def PERMISOS_BASE():
    """Permisos por defecto (sesión válida + MFA completa + email verificado).

    Se anteponen en los ViewSets que añaden RequiereRol/RequiereModulo, ya que fijar
    ``permission_classes`` reemplaza —no agrega— a los de ``DEFAULT_PERMISSION_CLASSES``.
    """
    return [IsAuthenticated, MFASesionCompleta, EmailVerificado]


class MFASesionCompleta(BasePermission):
    """Rechaza (403) tokens con sesión MFA incompleta (claim ``mfa="pending"``)."""

    message = "Sesión MFA incompleta: verifica tu segundo factor."

    def has_permission(self, request, view):
        token = request.auth
        if token is None:
            return True  # sin token autenticado: lo resuelve IsAuthenticated
        return token.get("mfa") != "pending"


class EmailVerificado(BasePermission):
    """Rechaza (403) actores cuyo email no está verificado (``email_verificado`` nulo)."""

    message = "Debes verificar tu correo electrónico para continuar."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return True  # lo resuelve IsAuthenticated
        # Si el modelo no define el campo, no bloquea (p. ej. actores sin verificación de email).
        if not hasattr(user, "email_verificado"):
            return True
        return user.email_verificado is not None
