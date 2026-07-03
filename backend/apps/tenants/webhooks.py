"""Webhook de Stripe (control plane, schema ``public``). Montado en ``config/urls_public.py``.

Va en la whitelist de enforcement: el cobro y sus eventos nunca se bloquean.
"""

from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.services.billing import procesar_evento_stripe
from apps.tenants.services.stripe_gateway import verificar_webhook


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            evento = verificar_webhook(request.body, request.META.get("HTTP_STRIPE_SIGNATURE"))
        except Exception:
            return Response({"detail": "Firma o payload inválido."}, status=400)
        resultado = procesar_evento_stripe(evento)
        return Response(resultado)
