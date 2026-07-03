"""Doble opt-in de email para altas externas (baseline suite).

Token firmado y con expiración (``django.core.signing`` sobre ``SECRET_KEY``, sin dependencias
extra) que ata la verificación a un actor y a su tenant. La vista corre en el data plane: valida
que el token sea de ESTE tenant (anti cross-tenant) y marca ``email_verificado``.
"""
from __future__ import annotations

from django.apps import apps as django_apps
from django.core import signing
from django.db import connection
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.jwt import CONTEXTS  # ctx -> (app_label, model_name)

SALT = "xenty-email-verify"
MAX_AGE = 60 * 60 * 48  # 48 horas


def generar_token(user, ctx: str) -> str:
    """Token de verificación para ``user`` en el schema actual."""
    return signing.dumps(
        {"ctx": ctx, "uid": user.pk, "tenant": connection.schema_name}, salt=SALT
    )


def build_verify_url(request, slug: str, token: str) -> str:
    """URL absoluta al endpoint de verificación en el subdominio del tenant.

    Deriva esquema y puerto del host de la petición (en dev, Nginx preserva ``:8080``) y cambia el
    subdominio por el del tenant recién creado, para que django-tenants resuelva el schema correcto.
    """
    from django.conf import settings

    host = request.get_host()
    puerto = f":{host.split(':', 1)[1]}" if ":" in host else ""
    base_domain = settings.TENANT_BASE_DOMAIN
    scheme = "https" if request.is_secure() else "http"
    return f"{scheme}://{slug}.{base_domain}{puerto}/api/auth/verificar-email/?token={token}"


class VerificarEmailView(APIView):
    """GET /api/auth/verificar-email/?token=… — marca el email como verificado (data plane)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        try:
            data = signing.loads(token, salt=SALT, max_age=MAX_AGE)
        except signing.SignatureExpired:
            return HttpResponse("El enlace de verificación expiró.", status=400)
        except signing.BadSignature:
            return HttpResponse("Enlace de verificación inválido.", status=400)

        if data.get("tenant") != connection.schema_name:
            return HttpResponse("El enlace no corresponde a este dominio.", status=400)

        ctx = data.get("ctx")
        if ctx not in CONTEXTS:
            return HttpResponse("Enlace inválido.", status=400)
        app_label, model_name = CONTEXTS[ctx]
        model = django_apps.get_model(app_label, model_name)
        user = model.objects.filter(pk=data.get("uid")).first()
        if user is None or not hasattr(user, "email_verificado"):
            return HttpResponse("La cuenta no existe.", status=404)

        if user.email_verificado is None:
            user.email_verificado = timezone.now()
            user.save(update_fields=["email_verificado"])

        return HttpResponse(
            "<h2>Correo verificado</h2><p>Tu correo quedó confirmado. Ya puedes iniciar sesión.</p>",
            content_type="text/html; charset=utf-8",
        )
