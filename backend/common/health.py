"""Endpoints de salud (baseline de la suite): liveness y readiness.

- ``GET /health/``        liveness: el proceso responde (no toca dependencias). 200 siempre.
- ``GET /health/ready/``  readiness: verifica DB y cache (Redis). 200 si todo ok, 503 si algo falla.

Sin autenticación ni contexto de tenant (rutas en la whitelist de enforcement, CLAUDE.md §6). No
exponen datos: solo el estado de las dependencias.
"""

from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LivenessView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        checks: dict[str, bool] = {}
        ok = True

        try:
            from django.db import connection

            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            checks["db"] = True
        except Exception:
            checks["db"] = False
            ok = False

        try:
            from django.core.cache import cache

            cache.set("healthz", "1", 5)
            checks["cache"] = cache.get("healthz") == "1"
            ok = ok and checks["cache"]
        except Exception:
            checks["cache"] = False
            ok = False

        return Response(
            {"status": "ready" if ok else "degraded", **checks},
            status=200 if ok else 503,
        )
