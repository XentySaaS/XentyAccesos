"""Vistas de autenticación compartidas por los dos contextos del tenant."""
from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from common.jwt import build_tokens


class _CredencialesSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class BaseLoginView(APIView):
    """Login por email/contraseña. Las subclases fijan ``model`` y ``ctx``.

    Respuesta genérica ante credenciales malas (no se distingue email inexistente de
    contraseña incorrecta) para no filtrar qué cuentas existen.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    model = None
    ctx: str = ""

    def post(self, request):
        s = _CredencialesSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        invalidas = Response({"detail": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            actor = self.model.objects.get(email=s.validated_data["email"].lower())
        except self.model.DoesNotExist:
            return invalidas
        if not actor.check_password(s.validated_data["password"]) or not actor.is_active:
            return invalidas
        return Response(build_tokens(actor, self.ctx))


class LogoutView(APIView):
    """Invalida el refresh token (lo añade a la blacklist del tenant)."""

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response({"detail": "Falta 'refresh'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)
