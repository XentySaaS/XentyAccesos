"""Idempotencia de peticiones mutadoras (evita registros duplicados por doble clic/reintento).

Un doble clic o un reintento de red puede reejecutar un POST y crear un registro duplicado. El
cliente manda un header ``Idempotency-Key`` único por operación (ver ``api/client.ts``); este
middleware, para métodos no seguros con ese header:

  1. Si ya hay una respuesta cacheada para ese key → la **repite** (no reejecuta la vista).
  2. Si hay otra petición idéntica en curso (lock) → responde **409** ("duplicada en proceso").
  3. Si no, adquiere el lock, ejecuta la vista y cachea la respuesta 2xx para repetirla.

El aislamiento por tenant es automático: la caché prefija cada clave con el schema activo
(``common.cache.tenant_key_func``), así el key de un tenant nunca colisiona con el de otro.
Debe ir DESPUÉS de ``TenantMainMiddleware`` (para que el schema ya esté resuelto) y de los
enforcement (para no cachear un 503/423).
"""
from __future__ import annotations

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH"})
_TTL = 60 * 10          # ventana de repetición de la respuesta (10 min)
_LOCK_TTL = 30          # vida del lock mientras la vista corre (segundos)


class Idempotency:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        key = request.headers.get("Idempotency-Key")
        if not key or request.method not in UNSAFE_METHODS:
            return self.get_response(request)

        base = f"idemp:{request.method}:{request.path}:{key}"
        cached = cache.get(base)
        if cached is not None:
            return HttpResponse(
                cached["content"], status=cached["status"],
                content_type=cached["content_type"],
            )

        # Lock anti-concurrencia: cache.add es atómico (solo entra el primero).
        if not cache.add(f"{base}:lock", "1", timeout=_LOCK_TTL):
            return JsonResponse(
                {"detail": "Solicitud duplicada en proceso. Espera la respuesta."},
                status=409,
            )

        try:
            response = self.get_response(request)
            if 200 <= response.status_code < 300:
                # DRF devuelve respuestas diferidas: hay que renderizarlas antes de leer content.
                if hasattr(response, "render") and not getattr(response, "is_rendered", True):
                    response.render()
                try:
                    contenido = response.content
                except Exception:  # noqa: BLE001 — respuesta en streaming u otra no cacheable
                    return response
                cache.set(base, {
                    "content": contenido,
                    "status": response.status_code,
                    "content_type": response.get("Content-Type", "application/json"),
                }, _TTL)
            return response
        finally:
            cache.delete(f"{base}:lock")
