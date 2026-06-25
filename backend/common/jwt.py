"""JWT consciente del tenant para los DOS contextos de autenticación del data plane.

Cada token lleva tres claims propios:
- ``ctx``      : "acceso" (Usuario) | "proveedores" (CuentaProveedor) — de qué modelo cargar el actor.
- ``tenant``   : ``schema_name`` del tenant emisor — se valida contra el schema de la petición
                 (rechaza tokens cruzados entre tenants, REMEDIACION §7 aislamiento).
- ``user_id``  : pk del actor dentro de ese schema.

Refresh con rotación + blacklist se delegan en SimpleJWT (``TokenRefreshView``): el refresh
preserva los claims al rotar y ``blacklist()`` opera por ``jti`` (válido para ambos contextos).
"""
from __future__ import annotations

from django.apps import apps as django_apps
from django.db import connection
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

# ctx -> (app_label, model_name). Carga perezosa para evitar ciclos de importación.
CONTEXTS = {
    "acceso": ("accounts", "Usuario"),
    "proveedores": ("proveedores", "CuentaProveedor"),
    "superadmin": ("tenants", "SuperAdmin"),  # control plane (schema public)
}


def build_tokens(user, ctx: str, *, mfa_pendiente: bool = False) -> dict[str, str]:
    """Emite par access/refresh con los claims ctx/tenant/user_id/mfa del schema actual.

    ``mfa_pendiente=True`` marca el token como sesión MFA incompleta (claim ``mfa="pending"``):
    solo sirve para completar el segundo factor; ``MFASesionCompleta`` rechaza el resto (F0.4).
    """
    if ctx not in CONTEXTS:
        raise ValueError(f"Contexto JWT desconocido: {ctx}")
    refresh = RefreshToken()
    refresh["user_id"] = user.pk
    refresh["ctx"] = ctx
    refresh["tenant"] = connection.schema_name
    refresh["mfa"] = "pending" if mfa_pendiente else "ok"
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class TenantAwareJWTAuthentication(JWTAuthentication):
    """Resuelve el actor desde el modelo correcto y exige que el token sea de este tenant."""

    def get_user(self, validated_token):
        ctx = validated_token.get("ctx")
        if ctx not in CONTEXTS:
            raise InvalidToken("El token no declara un contexto válido.")

        if validated_token.get("tenant") != connection.schema_name:
            # Token emitido para otro tenant (o para 'public'): no se acepta aquí.
            raise AuthenticationFailed("El token no pertenece a este tenant.")

        app_label, model_name = CONTEXTS[ctx]
        model = django_apps.get_model(app_label, model_name)
        try:
            user = model.objects.get(pk=validated_token["user_id"])
        except model.DoesNotExist:
            raise AuthenticationFailed("El actor del token no existe en este tenant.")

        if not user.is_active:
            raise AuthenticationFailed("Cuenta inactiva.")
        return user
