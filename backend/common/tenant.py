"""Utilidades del tenant activo, compartidas por las notificaciones.

Punto único para obtener el **nombre display** del tenant (p. ej. «3 Museos») en vez del
``schema_name`` técnico (p. ej. «museos»), que es lo que debe aparecer como remitente/invitador en
correos y WhatsApp.
"""

from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def nombre_tenant_actual(default: str = "Xenty Accesos") -> str:
    """Nombre display del tenant activo, para mostrarlo como quien invita/notifica.

    Resuelve desde ``connection.tenant`` (contexto de request o ``tenant_context``). Bajo
    ``schema_context`` el tenant es un *FakeTenant* sin ``nombre``: en ese caso se consulta el modelo
    por ``schema_name``. Devuelve ``default`` si no hay tenant (schema público / control plane).
    """
    from django.db import connection
    from django_tenants.utils import get_public_schema_name, get_tenant_model

    t = getattr(connection, "tenant", None)
    nombre = getattr(t, "nombre", None)
    if nombre:
        return nombre
    schema = getattr(connection, "schema_name", None)
    if schema and schema != get_public_schema_name():
        obj = get_tenant_model().objects.filter(schema_name=schema).first()
        if obj is not None:
            return obj.nombre
    return default


class MarcaTenantView(APIView):
    """``GET /api/publico/marca/`` — nombre display del tenant del host (público, sin auth).

    Lo usan las pantallas públicas de los SPAs del tenant (p. ej. el login de proveedores muestra
    «Portal de proveedores de 3 Museos»). No expone nada sensible: el nombre ya figura en cada
    correo/WhatsApp que el tenant envía.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"nombre": nombre_tenant_actual()})
