"""Hub de login de proveedores (``proveedores.dominio``) — control plane, schema public.

El hub SOLO descubre espacios: nunca maneja contraseñas ni emite tokens. El login real ocurre en
el panel del tenant elegido (``<slug>.proveedores.dominio``), con el flujo JWT existente intacto.

Flujo:
1. ``POST espacios/`` ``{email}`` — si el dispositivo ya está verificado para ese correo (cookie
   firmada, 90 días), devuelve los espacios. Si el correo no tiene cuenta de proveedor activa,
   responde ``registrado: False`` (la UI lo dice en el primer paso, sin pantalla de código). Si
   la tiene, envía un código de 6 dígitos y pide verificación.
2. ``POST espacios/verificar/`` ``{email, codigo}`` — valida el código (hash + ``compare_digest``,
   máx. 5 intentos, TTL 10 min), deja la cookie de dispositivo y devuelve los espacios.

Enumeración (decisión de producto 2026-07-21): se revela solo la EXISTENCIA de la cuenta
(booleano, con rate limit por IP) para no mandar a un callejón sin salida a quien no tiene
cuenta; la parte sensible —EN QUÉ recintos trabaja el correo— sigue exigiendo probar la
propiedad del correo (código o cookie de dispositivo).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from django.core import signing
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import DirectorioProveedor, Domain, Tenant

COOKIE_DISPOSITIVO = "xhub_prov"
SALT_DISPOSITIVO = "hub-proveedores-dispositivo"
MAX_AGE_DISPOSITIVO = 90 * 24 * 3600  # el código se pide una vez por dispositivo (90 días)
TTL_CODIGO = 10 * 60
MAX_INTENTOS = 5  # 6 dígitos + 5 intentos + TTL 10 min ⇒ fuerza bruta inviable
MAX_CODIGOS_HORA = 3  # cooldown de envío por correo (anti spam/mail-bombing)

_RESPUESTA_CODIGO = {
    "verificado": False,
    "registrado": True,
    "detail": "Te enviamos un código de verificación a tu correo.",
}
_RESPUESTA_NO_REGISTRADO = {
    "verificado": False,
    "registrado": False,
    "detail": "Este correo no tiene una cuenta de proveedor activa.",
}


def _hash(codigo: str) -> str:
    return hashlib.sha256(codigo.encode()).hexdigest()


def _espacios(email: str, request) -> list[dict]:
    """Espacios activos del correo, con la URL del panel de cada tenant.

    Esquema y puerto se heredan de la petición del hub (dev conserva ``:8080``); el dominio del
    panel sale de la tabla ``Domain`` (``es_panel_proveedores=True``). Tenants suspendidos o
    cancelados no se listan (el enforcement los bloquearía de todos modos).
    """
    host = request.get_host()
    _, _, puerto = host.partition(":")
    sufijo = f":{puerto}" if puerto else ""
    entradas = (
        DirectorioProveedor.objects.filter(
            email=email,
            activo=True,
            tenant__estado__in=[Tenant.Estado.TRIAL, Tenant.Estado.ACTIVO],
        )
        .select_related("tenant")
        .order_by("tenant__nombre")
    )
    espacios = []
    for e in entradas:
        d = Domain.objects.filter(tenant=e.tenant, es_panel_proveedores=True).first()
        if d is None:  # tenant sin dominio de panel (backfill pendiente): no se puede rutear
            continue
        espacios.append(
            {
                "nombre": e.tenant.nombre,
                "dominio": d.domain,
                "url": f"{request.scheme}://{d.domain}{sufijo}",
            }
        )
    return espacios


def _dispositivo_verificado(request, email: str) -> bool:
    crudo = request.COOKIES.get(COOKIE_DISPOSITIVO, "")
    if not crudo:
        return False
    try:
        data = signing.loads(crudo, salt=SALT_DISPOSITIVO, max_age=MAX_AGE_DISPOSITIVO)
    except signing.BadSignature:
        return False
    return hmac.compare_digest(str(data.get("email", "")), email)


def _poner_cookie_dispositivo(response, request, email: str) -> None:
    response.set_cookie(
        COOKIE_DISPOSITIVO,
        signing.dumps({"email": email}, salt=SALT_DISPOSITIVO),
        max_age=MAX_AGE_DISPOSITIVO,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure(),
    )


class _EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class _CodigoSerializer(_EmailSerializer):
    codigo = serializers.CharField(max_length=12)


@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="post")
class EspaciosProveedorView(APIView):
    """Paso 1: espacios del correo, o envío del código si el dispositivo no está verificado."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        s = _EmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].lower()

        if _dispositivo_verificado(request, email):
            return Response({"verificado": True, "espacios": _espacios(email, request)})

        # Cuenta activa en al menos un tenant vivo (a tenants suspendidos/cancelados no se
        # puede entrar de todos modos, así que no vale la pena un código para verlos).
        registrado = DirectorioProveedor.objects.filter(
            email=email,
            activo=True,
            tenant__estado__in=[Tenant.Estado.TRIAL, Tenant.Estado.ACTIVO],
        ).exists()
        if not registrado:
            return Response(_RESPUESTA_NO_REGISTRADO)

        clave_envios = f"hubprov:envios:{email}"
        envios = cache.get(clave_envios, 0)
        if envios < MAX_CODIGOS_HORA:
            codigo = f"{secrets.randbelow(1_000_000):06d}"
            cache.set(f"hubprov:codigo:{email}", _hash(codigo), TTL_CODIGO)
            cache.delete(f"hubprov:intentos:{email}")
            cache.set(clave_envios, envios + 1, 3600)
            from common.emails import enviar_codigo_espacios

            enviar_codigo_espacios(email_destino=email, codigo=codigo)
        return Response(_RESPUESTA_CODIGO)


@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="post")
class VerificarEspaciosView(APIView):
    """Paso 2: valida el código, deja la cookie de dispositivo y devuelve los espacios."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        s = _CodigoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].lower()
        codigo = s.validated_data["codigo"].strip()
        invalido = Response({"detail": "Código inválido o expirado."}, status=400)

        clave_codigo = f"hubprov:codigo:{email}"
        esperado = cache.get(clave_codigo)
        if not esperado:
            return invalido

        clave_intentos = f"hubprov:intentos:{email}"
        try:
            intentos = cache.incr(clave_intentos)
        except ValueError:  # aún no existe el contador
            cache.set(clave_intentos, 1, TTL_CODIGO)
            intentos = 1
        if intentos > MAX_INTENTOS:
            cache.delete(clave_codigo)  # código quemado: hay que solicitar uno nuevo
            return invalido

        if not hmac.compare_digest(_hash(codigo), esperado):
            return invalido

        cache.delete(clave_codigo)
        cache.delete(clave_intentos)
        respuesta = Response({"verificado": True, "espacios": _espacios(email, request)})
        _poner_cookie_dispositivo(respuesta, request, email)
        return respuesta
