"""Autenticación HMAC de dispositivos edge (REMEDIATION §A1).

Firma sobre ``METHOD-PATH-TIMESTAMP`` con el token del dispositivo (``compare_digest``), ventana de
tiempo y **nonce de un solo uso** (anti-replay en Redis). El dispositivo vive en ``public`` y queda
ligado a su tenant; toda operación posterior corre dentro de ``tenant_context`` (aislamiento, §C7).
"""

from __future__ import annotations

import hashlib
import hmac
import time

from django.core.cache import cache
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

VENTANA_SEG = 300


def firmar_peticion(token: str, method: str, path: str, timestamp: str | int) -> str:
    """Calcula la firma HMAC-SHA256 (la usan el dispositivo y las pruebas)."""
    mensaje = f"{method.upper()}-{path}-{timestamp}".encode()
    return hmac.new(token.encode(), mensaje, hashlib.sha256).hexdigest()


class EdgeHMACAuthentication(BaseAuthentication):
    def authenticate(self, request):
        h = request.headers
        mac, ts, nonce, firma = (
            h.get("X-Edge-Mac"),
            h.get("X-Edge-Timestamp"),
            h.get("X-Edge-Nonce"),
            h.get("X-Edge-Signature"),
        )
        if not all([mac, ts, nonce, firma]):
            return None  # no es una petición edge

        from apps.tenants.models import DispositivoEdge

        with schema_context(get_public_schema_name()):
            device = (
                DispositivoEdge.objects.select_related("tenant").filter(mac_address=mac).first()
            )
        if device is None:
            raise AuthenticationFailed("Dispositivo desconocido.")

        try:
            desfase = abs(time.time() - int(ts))
        except (TypeError, ValueError):
            raise AuthenticationFailed("Timestamp inválido.")
        if desfase > VENTANA_SEG:
            raise AuthenticationFailed("Petición fuera de la ventana de tiempo.")

        esperada = firmar_peticion(device.token, request.method, request.path, ts)
        if not hmac.compare_digest(esperada, firma):
            raise AuthenticationFailed("Firma HMAC inválida.")

        # Anti-replay: el nonce se consume una sola vez (TTL = ventana).
        if not cache.add(f"edge:nonce:{device.id}:{nonce}", 1, timeout=VENTANA_SEG):
            raise AuthenticationFailed("Nonce reutilizado (replay).")

        request.dispositivo = device
        return (device, None)
