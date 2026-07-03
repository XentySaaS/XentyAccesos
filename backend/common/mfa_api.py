"""Endpoints de MFA por TOTP, comunes a los contextos del tenant.

Flujo:
  1. ``POST /api/auth/mfa/totp/enrolar/``   (sesión completa) → genera secreto + URI/QR (no activa).
  2. ``POST /api/auth/mfa/totp/activar/``   (sesión completa) → verifica 1er código y activa MFA.
  3. ``POST /api/auth/mfa/verificar/``      (sesión MFA pendiente, tras login) → emite tokens full.
"""

from __future__ import annotations

import base64
import io

import qrcode
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.jwt import build_tokens
from common.mfa import generar_secreto, uri_aprovisionamiento, verificar_totp


def _ctx_de(request) -> str:
    return (request.auth or {}).get("ctx", "")


def _qr_data_uri(texto: str) -> str:
    """PNG en base64 (data URI) del QR. Se genera en el servidor: el secreto TOTP nunca se
    envía a un servicio de QR externo."""
    img = qrcode.make(texto)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class _CodigoSerializer(serializers.Serializer):
    codigo = serializers.CharField()


class EnrolarTOTPView(APIView):
    """Genera un secreto TOTP para el actor y devuelve el URI de aprovisionamiento (QR)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not hasattr(user, "mfa_totp_secret"):
            return Response({"detail": "MFA no disponible para este actor."}, status=400)
        secreto = generar_secreto()
        user.mfa_totp_secret = secreto
        user.save(update_fields=["mfa_totp_secret"])
        uri = uri_aprovisionamiento(secreto, user.email)
        return Response({"secret": secreto, "otpauth_uri": uri, "qr": _qr_data_uri(uri)})


class ActivarTOTPView(APIView):
    """Verifica el primer código y activa el MFA del actor."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = _CodigoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = request.user
        if not getattr(user, "mfa_totp_secret", None):
            return Response({"detail": "No hay un secreto TOTP enrolado."}, status=400)
        if not verificar_totp(user.mfa_totp_secret, s.validated_data["codigo"]):
            return Response({"detail": "Código TOTP inválido."}, status=400)
        user.mfa_habilitado = True
        user.save(update_fields=["mfa_habilitado"])
        return Response({"detail": "MFA activado."})


class VerificarMFAView(APIView):
    """Completa la sesión: con un token MFA pendiente + código TOTP, emite tokens 'full'."""

    permission_classes = [IsAuthenticated]  # exento de MFASesionCompleta a propósito

    def post(self, request):
        s = _CodigoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if (request.auth or {}).get("mfa") != "pending":
            return Response({"detail": "La sesión no requiere verificación MFA."}, status=400)
        user = request.user
        if not verificar_totp(getattr(user, "mfa_totp_secret", None), s.validated_data["codigo"]):
            return Response({"detail": "Código TOTP inválido."}, status=400)
        return Response(build_tokens(user, _ctx_de(request), mfa_pendiente=False))
