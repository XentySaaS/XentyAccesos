"""Manejador de excepciones DRF del proyecto.

Convierte ``Ratelimited`` (django-ratelimit, subclase de PermissionDenied) en un **429** con
mensaje claro, en vez del 403 genérico de DRF (REMEDIACION §A4: superar el umbral → 429).
El resto de excepciones siguen el manejo estándar de DRF.
"""
from __future__ import annotations

from django_ratelimit.exceptions import Ratelimited
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def drf_exception_handler(exc, context):
    if isinstance(exc, Ratelimited):
        return Response(
            {"detail": "Demasiadas solicitudes. Espera un momento e intenta de nuevo."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    return exception_handler(exc, context)
