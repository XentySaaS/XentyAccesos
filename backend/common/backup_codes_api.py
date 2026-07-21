"""Endpoints de códigos de respaldo (recovery codes), comunes a los actores con MFA.

Actor-agnóstico: operan sobre ``request.user.codigos_respaldo`` (mismo related_name en cada actor).
- ``POST /api/auth/mfa/respaldo/generar/``   → genera/regenera; devuelve los 10 EN CLARO una vez.
- ``POST /api/auth/mfa/respaldo/verificar/`` → (sesión MFA pendiente) consume un código y da tokens.
"""

from __future__ import annotations

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common import backup_codes
from common.jwt import build_tokens


def _ctx_de(request) -> str:
    return (request.auth or {}).get("ctx", "")


class _CodigoSerializer(serializers.Serializer):
    codigo = serializers.CharField()


# Límite modesto: generar/regenerar es raro y autenticado; frena scripts abusivos.
@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True), name="post")
class GenerarCodigosRespaldoView(APIView):
    """Genera (o regenera) los códigos de respaldo del actor. Los devuelve EN CLARO una sola vez.

    Regenerar (cuando ya existen códigos) exige **reautenticación** con la contraseña, porque invalida
    los anteriores. La primera generación solo requiere estar autenticado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not hasattr(user, "codigos_respaldo"):
            return Response(
                {"detail": "Los códigos de respaldo no están disponibles para este actor."},
                status=400,
            )
        manager = user.codigos_respaldo
        if backup_codes.total(manager) > 0:
            password = (request.data or {}).get("password") or ""
            if not user.check_password(password):
                return Response(
                    {"detail": "Contraseña incorrecta. Reautentícate para regenerar."}, status=403
                )
        codigos = backup_codes.regenerar(manager)
        return Response({"codigos": codigos, "total": len(codigos)})


# Rate limit anti fuerza bruta del 2º factor (igual que el login).
@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="post")
class VerificarCodigoRespaldoView(APIView):
    """Completa la sesión MFA pendiente con un código de respaldo (alternativa a TOTP/llave)."""

    permission_classes = [IsAuthenticated]  # token MFA pendiente; exento de MFASesionCompleta

    def post(self, request):
        s = _CodigoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if (request.auth or {}).get("mfa") != "pending":
            return Response({"detail": "La sesión no requiere verificación MFA."}, status=400)
        user = request.user
        if not hasattr(user, "codigos_respaldo") or not backup_codes.consumir(
            user.codigos_respaldo, s.validated_data["codigo"]
        ):
            return Response({"detail": "Código de respaldo inválido."}, status=400)
        return Response(build_tokens(user, _ctx_de(request), mfa_pendiente=False))
