"""Recuperación de contraseña self-service para los dos contextos del tenant (acceso, proveedores).

Token firmado y con expiración (``django.core.signing`` sobre ``SECRET_KEY``, sin dependencias
extra, mismo enfoque que ``common.email_verify``) que ata el reset a un actor, su tenant y su
contraseña actual:

- ``tenant``: ``schema_name`` emisor → se valida contra el schema de la petición (anti cross-tenant).
- ``ctx``:    "acceso" | "proveedores" → el token de un contexto no sirve en el otro.
- ``uid``:    pk del actor.
- ``pw``:     huella de la contraseña actual → al cambiarla el token queda invalidado (un solo uso).

Sin enumeración de usuarios: ``solicitar`` responde siempre igual, exista o no el correo.
"""

from __future__ import annotations

import hashlib

from django.core import signing
from django.db import connection
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

SALT = "xenty-password-reset"
MAX_AGE = 60 * 60  # 1 hora

# Respuesta única de ``solicitar`` (no revela si el correo existe).
_RESPUESTA_GENERICA = {
    "detail": "Si el correo está registrado, te enviamos instrucciones para restablecer tu contraseña."
}


def _huella(user) -> str:
    """Huella corta de la contraseña actual. Cambia al hacer ``set_password`` → token de un solo uso."""
    return hashlib.sha256(user.password.encode()).hexdigest()[:16]


def generar_token_reset(user, ctx: str) -> str:
    """Token de restablecimiento para ``user`` en el schema actual."""
    return signing.dumps(
        {"ctx": ctx, "uid": user.pk, "tenant": connection.schema_name, "pw": _huella(user)},
        salt=SALT,
    )


def build_reset_url(request, ctx: str, token: str) -> str:
    """URL absoluta a la pantalla de restablecimiento del SPA correspondiente.

    Deriva esquema/host de la petición (que llega al subdominio del tenant), de modo que el enlace
    conserva el contexto de tenant. El SPA de proveedores se sirve bajo ``/proveedores``.
    """
    host = request.get_host()
    scheme = "https" if request.is_secure() else "http"
    prefijo = "/proveedores" if ctx == "proveedores" else ""
    return f"{scheme}://{host}{prefijo}/restablecer?token={token}"


class _EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class _ConfirmarSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, trim_whitespace=False)


@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")
class SolicitarResetBase(APIView):
    """Envía el correo con el enlace de restablecimiento. Las subclases fijan ``model`` y ``ctx``.

    Responde siempre igual (200) para no filtrar qué correos existen. El envío es best-effort.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]
    model = None
    ctx: str = ""

    def post(self, request):
        s = _EmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        actor = self.model.objects.filter(
            email=s.validated_data["email"].lower(), activo=True
        ).first()
        if actor is not None:
            from common.emails import enviar_reset_password

            token = generar_token_reset(actor, self.ctx)
            nombre_tenant = (
                getattr(getattr(request, "tenant", None), "nombre", "") or "Xenty Acceso"
            )
            enviar_reset_password(
                email_destino=actor.email,
                nombre=getattr(actor, "nombre", "") or "",
                nombre_tenant=nombre_tenant,
                url=build_reset_url(request, self.ctx, token),
                telefono=getattr(actor, "telefono", None),
            )
        return Response(_RESPUESTA_GENERICA)


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True), name="post")
class ConfirmarResetBase(APIView):
    """Valida el token y fija la nueva contraseña. Las subclases fijan ``model`` y ``ctx``."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    model = None
    ctx: str = ""

    def post(self, request):
        s = _ConfirmarSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        invalido = Response(
            {"detail": "El enlace de restablecimiento es inválido o ya expiró."}, status=400
        )
        try:
            data = signing.loads(s.validated_data["token"], salt=SALT, max_age=MAX_AGE)
        except signing.BadSignature:
            return invalido

        if data.get("tenant") != connection.schema_name or data.get("ctx") != self.ctx:
            return invalido

        actor = self.model.objects.filter(pk=data.get("uid"), activo=True).first()
        if actor is None or data.get("pw") != _huella(actor):
            # Huella distinta ⇒ la contraseña ya cambió (token de un solo uso, ya utilizado).
            return invalido

        actor.set_password(s.validated_data["password"])
        actor.save(update_fields=["password"])
        return Response({"detail": "Tu contraseña se actualizó. Ya puedes iniciar sesión."})
