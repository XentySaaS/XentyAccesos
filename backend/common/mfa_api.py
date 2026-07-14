"""Endpoints de MFA por TOTP, comunes a los contextos del tenant.

Flujo:
  1. ``POST /api/auth/mfa/totp/enrolar/``   → genera secreto + URI/QR y lo guarda EN CACHE (no en la
                                              BD): un enrolamiento abandonado no deja estado a medias.
  2. ``POST /api/auth/mfa/totp/activar/``   → verifica el 1er código contra el secreto en cache y,
                                              recién ahí, lo persiste y activa el MFA.
  3. ``POST /api/auth/mfa/verificar/``      (sesión MFA pendiente, tras login) → emite tokens full.
"""

from __future__ import annotations

import base64
import io

import qrcode
from django.core.cache import cache
from django.db import connection
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.jwt import build_tokens
from common.mfa import generar_secreto, uri_aprovisionamiento, verificar_totp

# Segundos para completar el enrolamiento (escanear el QR + confirmar el 1er código).
_ENROL_TTL = 600


def _ctx_de(request) -> str:
    return (request.auth or {}).get("ctx", "")


def _enrol_key(request) -> str:
    """Clave de cache del secreto TOTP en curso de enrolamiento (aislada por ctx + schema + actor)."""
    return f"mfa:totp:enrol:{_ctx_de(request)}:{connection.schema_name}:{request.user.pk}"


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
        # El secreto NO se persiste al mostrar el QR: se guarda en cache hasta que el usuario
        # confirme el 1er código (ActivarTOTPView). Así un enrolamiento abandonado no deja al actor
        # "a medio enrolar" (con MFA obligatorio, el login lo tomaba como enrolado y pedía un código
        # que el usuario nunca llegó a escanear). Si ya hay uno en curso se reutiliza, para que
        # recargar el QR no invalide el que el usuario ya escaneó.
        secreto = cache.get(_enrol_key(request)) or generar_secreto()
        cache.set(_enrol_key(request), secreto, _ENROL_TTL)
        uri = uri_aprovisionamiento(secreto, user.email)
        return Response({"secret": secreto, "otpauth_uri": uri, "qr": _qr_data_uri(uri)})


class ActivarTOTPView(APIView):
    """Verifica el primer código y activa el MFA del actor.

    Si se invoca dentro de una sesión MFA **pendiente** (enrolamiento obligatorio tras el login),
    la activación prueba de por sí el 2º factor, así que además se emiten tokens 'full' para no
    exigir un segundo código en la vista de verificación.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = _CodigoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = request.user
        secreto = cache.get(_enrol_key(request))
        if not secreto:
            return Response(
                {"detail": "El enrolamiento expiró. Vuelve a generar el código QR."}, status=400
            )
        if not verificar_totp(secreto, s.validated_data["codigo"]):
            return Response({"detail": "Código TOTP inválido."}, status=400)
        # Confirmado: recién aquí se persiste el secreto y se activa el MFA.
        user.mfa_totp_secret = secreto
        user.mfa_habilitado = True
        user.save(update_fields=["mfa_totp_secret", "mfa_habilitado"])
        cache.delete(_enrol_key(request))
        data = {"detail": "MFA activado."}
        if (request.auth or {}).get("mfa") == "pending":
            data.update(build_tokens(user, _ctx_de(request), mfa_pendiente=False))
        return Response(data)


class DesactivarTOTPView(APIView):
    """Desactiva el 2º factor por TOTP del actor (borra el secreto persistido).

    Si el actor no tiene otros métodos MFA (WebAuthn), el MFA queda deshabilitado por completo; si
    conserva llaves WebAuthn, el MFA sigue activo por esa vía. Idempotente: desactivar cuando no hay
    TOTP no falla.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not hasattr(user, "mfa_totp_secret"):
            return Response({"detail": "MFA no disponible para este actor."}, status=400)
        user.mfa_totp_secret = None
        tiene_webauthn = (
            user.credenciales_webauthn.exists() if hasattr(user, "credenciales_webauthn") else False
        )
        user.mfa_habilitado = tiene_webauthn
        user.save(update_fields=["mfa_totp_secret", "mfa_habilitado"])
        cache.delete(_enrol_key(request))  # descarta cualquier enrolamiento en curso
        return Response({"detail": "TOTP desactivado."})


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
