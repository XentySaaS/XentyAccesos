"""Receptor del webhook de estados de entrega del XCC (control plane, schema ``public``).

El Connector (repo ``xenty-connector``) notifica ``delivered/read/failed`` de cada mensaje que envió,
firmado con HMAC (mismo esquema que el edge y el ``ConnectorProvider`` de F-D). Aquí verificamos la
firma sobre el cuerpo crudo, la ventana temporal y el nonce anti-replay (Redis), y actualizamos el
estado del ``DestinatarioMensaje`` en el schema del tenant, correlacionando por ``external_id``
(= ``message_id`` que devolvió ``/v1/messages``).

Idempotente y **solo avanza** el estado (``entregado`` no pisa ``leido``). Va en el schema public y sin
auth (como el webhook de Stripe): su autenticación es la firma HMAC, no un JWT.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Ventana anti-replay (segundos). Igual que el edge y el Connector.
_WINDOW_SEC = 300
_ESTADOS_VALIDOS = {"delivered", "read", "failed"}


def _firma_valida(
    secret: str, method: str, path: str, tenant: str, ts: str, nonce: str, body: bytes, firma: str
) -> bool:
    body_hash = hashlib.sha256(body).hexdigest()
    signing = f"{method.upper()}\n{path}\n{tenant}\n{ts}\n{nonce}\n{body_hash}"
    esperada = hmac.new(secret.encode(), signing.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, firma or "")


@method_decorator(csrf_exempt, name="dispatch")
class ConnectorWebhookView(APIView):
    """POST /api/mensajeria/connector/webhook/ — estados de entrega del XCC (delivered/read/failed)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        tenant = request.META.get("HTTP_X_XCC_TENANT", "")
        ts = request.META.get("HTTP_X_XCC_TIMESTAMP", "")
        nonce = request.META.get("HTTP_X_XCC_NONCE", "")
        firma = request.META.get("HTTP_X_XCC_SIGNATURE", "")
        body = request.body  # bytes crudos: la firma es sobre estos bytes exactos

        if not (tenant and ts and nonce and firma):
            return Response({"detail": "Faltan cabeceras de autenticación HMAC."}, status=401)

        # Secreto global del Connector (schema public); sin él no hay cómo verificar la firma.
        from apps.tenants.models import ConfiguracionConnector

        with schema_context(get_public_schema_name()):
            cfg = ConfiguracionConnector.objects.first()
            secret = cfg.hmac_secret if cfg else None
        if not secret:
            return Response({"detail": "Connector no configurado."}, status=400)

        try:
            if abs(time.time() - int(ts)) > _WINDOW_SEC:
                return Response({"detail": "Petición fuera de la ventana de tiempo."}, status=401)
        except ValueError:
            return Response({"detail": "Timestamp inválido."}, status=401)

        if not _firma_valida(secret, "POST", request.path, tenant, ts, nonce, body, firma):
            return Response({"detail": "Firma HMAC inválida."}, status=401)

        # Anti-replay: nonce de un solo uso por (tenant, nonce) dentro de la ventana.
        if not cache.add(f"xcc:webhook:nonce:{tenant}:{nonce}", 1, timeout=_WINDOW_SEC):
            return Response({"detail": "Nonce reutilizado (replay)."}, status=401)

        try:
            datos = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return Response({"detail": "JSON inválido."}, status=400)

        # Scoping por tenant: el cuerpo debe declarar el mismo tenant que firmó.
        if datos.get("tenant") != tenant:
            return Response(
                {"detail": "El tenant del cuerpo no coincide con el firmado."}, status=403
            )

        message_id = str(datos.get("message_id") or "")
        estado_ext = datos.get("status")
        if not message_id or estado_ext not in _ESTADOS_VALIDOS:
            return Response({"detail": "Payload incompleto o estado no soportado."}, status=422)

        actualizados = _aplicar_estado(tenant, message_id, estado_ext)
        return Response({"ok": True, "actualizados": actualizados})


def _aplicar_estado(tenant: str, message_id: str, estado_ext: str) -> int:
    """Actualiza el ledger del tenant. Solo avanza el estado; ``failed`` no pisa entregado/leído."""
    from .models import DestinatarioMensaje as DM

    # Orden de progreso: un webhook tardío (delivered) no debe retroceder un estado más avanzado (read).
    rango = {
        DM.Estado.PENDIENTE: 0,
        DM.Estado.ENVIADO: 1,
        DM.Estado.ENTREGADO: 2,
        DM.Estado.LEIDO: 3,
    }
    destino = {
        "delivered": DM.Estado.ENTREGADO,
        "read": DM.Estado.LEIDO,
        "failed": DM.Estado.FALLIDO,
    }[estado_ext]

    n = 0
    with schema_context(tenant):
        for dm in DM.objects.filter(external_id=message_id):
            if estado_ext == "failed":
                # Un fallo tardío solo aplica si aún no se había confirmado entrega/lectura.
                if dm.estado in (DM.Estado.PENDIENTE, DM.Estado.ENVIADO):
                    dm.estado = DM.Estado.FALLIDO
                    dm.save(update_fields=["estado"])
                    n += 1
            elif rango.get(dm.estado, 0) < rango[destino]:
                dm.estado = destino
                dm.save(update_fields=["estado"])
                n += 1
    return n
