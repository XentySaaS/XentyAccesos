"""Permission classes globales de enforcement por ACTOR (CLAUDE.md §6, slots 5 y 9).

Se aplican vía ``DEFAULT_PERMISSION_CLASSES``. A diferencia de los enforcement por tenant (que son
middleware sobre ``request.tenant``), estos dependen del actor autenticado y por eso viven en la
capa DRF, donde la autenticación JWT ya resolvió ``request.user`` / ``request.auth``.

Endpoints que deben quedar exentos (login, verificación MFA) fijan su propio ``permission_classes``.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission


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
