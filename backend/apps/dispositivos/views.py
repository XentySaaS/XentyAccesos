"""API edge ``/api/v1/*`` (HMAC + rate limit). Long-poll de comandos y validación de QR."""

from __future__ import annotations

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import EdgeHMACAuthentication
from .services import ack_comando, pull_comandos, validar_qr_edge


class EsDispositivo(BasePermission):
    message = "Requiere autenticación de dispositivo edge."

    def has_permission(self, request, view):
        return getattr(request, "dispositivo", None) is not None


_RATE = method_decorator(ratelimit(key="ip", rate="120/m", method="POST", block=True), name="post")


class _EdgeView(APIView):
    authentication_classes = [EdgeHMACAuthentication]
    permission_classes = [EsDispositivo]


class ComandosPullView(_EdgeView):
    """GET /api/v1/comandos/ — entrega los comandos pendientes del dispositivo (los marca enviados)."""

    def get(self, request):
        comandos = pull_comandos(request.dispositivo)
        return Response(
            [
                {
                    "id": c.id,
                    "tipo": c.tipo,
                    "port": c.port,
                    "duration_ms": c.duration_ms,
                    "texto": c.texto,
                    "timeout_sec": c.timeout_sec,
                }
                for c in comandos
            ]
        )


class ComandoAckView(_EdgeView):
    """POST /api/v1/comandos/<id>/ack/ — confirma un comando (solo si es de este dispositivo)."""

    def post(self, request, comando_id):
        n = ack_comando(request.dispositivo, comando_id)
        if n == 0:
            return Response({"detail": "Comando no encontrado para este dispositivo."}, status=404)
        return Response({"ack": True})


@method_decorator(ratelimit(key="ip", rate="240/m", method="POST", block=True), name="post")
class ValidarQREdgeView(_EdgeView):
    """POST /api/v1/validar-qr/ {qr} — valida el QR dentro del tenant del dispositivo."""

    def post(self, request):
        permitido, motivo = validar_qr_edge(request.dispositivo, request.data.get("qr", ""))
        return Response({"permitido": permitido, "motivo": motivo})
