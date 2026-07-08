"""Endpoints WebAuthn (2º factor), comunes al super-admin (control plane) y al Usuario del tenant.

Espejo de los endpoints TOTP: mismas permisiones y mismo flujo de sesión (``mfa="pending"`` → tokens
full). Las vistas operan sobre ``request.user`` y ``ctx`` del token, y guardan/leen credenciales en el
schema correcto (aislamiento). WebAuthn no está disponible para el contexto ``proveedores`` en este
slice (no tiene UI de MFA aún).
"""

from __future__ import annotations

from django.db import connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common import webauthn
from common.jwt import build_tokens


def _ctx(request) -> str:
    return (request.auth or {}).get("ctx", "")


def _soportado(ctx: str) -> bool:
    return webauthn.cred_model(ctx) is not None


class RegistroOpcionesView(APIView):
    """POST …/webauthn/registro/opciones/ — opciones de creación de credencial (sesión completa)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ctx = _ctx(request)
        if not _soportado(ctx):
            return Response({"detail": "WebAuthn no disponible para este actor."}, status=400)
        return Response(webauthn.opciones_registro(request.user, ctx, connection.schema_name))


class RegistroVerificarView(APIView):
    """POST …/webauthn/registro/verificar/ — verifica la attestation y guarda la credencial."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ctx = _ctx(request)
        if not _soportado(ctx):
            return Response({"detail": "WebAuthn no disponible para este actor."}, status=400)
        credential = (request.data or {}).get("credential")
        if not credential:
            return Response({"detail": "Falta la credencial."}, status=400)
        ok, error = webauthn.registrar(
            request.user,
            ctx,
            connection.schema_name,
            credential,
            (request.data or {}).get("nombre"),
        )
        if not ok:
            return Response({"detail": error}, status=400)
        return Response({"detail": "Llave registrada."})


class LoginOpcionesView(APIView):
    """POST …/webauthn/login/opciones/ — opciones de autenticación (con token MFA pendiente)."""

    permission_classes = [IsAuthenticated]  # exento de MFASesionCompleta a propósito

    def post(self, request):
        ctx = _ctx(request)
        if not _soportado(ctx):
            return Response({"detail": "WebAuthn no disponible para este actor."}, status=400)
        return Response(webauthn.opciones_login(request.user, ctx, connection.schema_name))


class LoginVerificarView(APIView):
    """POST …/webauthn/login/verificar/ — verifica la assertion y emite tokens 'full'."""

    permission_classes = [IsAuthenticated]  # exento de MFASesionCompleta a propósito

    def post(self, request):
        ctx = _ctx(request)
        if not _soportado(ctx):
            return Response({"detail": "WebAuthn no disponible para este actor."}, status=400)
        if (request.auth or {}).get("mfa") != "pending":
            return Response({"detail": "La sesión no requiere verificación MFA."}, status=400)
        credential = (request.data or {}).get("credential")
        if not credential:
            return Response({"detail": "Falta la credencial."}, status=400)
        ok, error = webauthn.verificar_login(request.user, ctx, connection.schema_name, credential)
        if not ok:
            return Response({"detail": error}, status=400)
        return Response(build_tokens(request.user, ctx, mfa_pendiente=False))
