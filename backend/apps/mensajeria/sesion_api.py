"""Sesión de WhatsApp del tenant vía el XCC (proxy firmado, data plane).

El admin del tenant vincula su número (ver QR), consulta el estado y desvincula desde la SPA; el
backend firma las peticiones al Connector. La conexión es la del tenant
(``PreferenciaMensajeria.connection_id``, default ``principal``).
"""

from __future__ import annotations

from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .connector_client import ConnectorNoDisponible, solicitar

_PERMS = [
    *PERMISOS_BASE(),
    ContextoAcceso,
    RequiereModulo("mensajeria"),
    RequiereRol("administrador"),
]


def _conn_id() -> str:
    from .models import PreferenciaMensajeria

    pref = PreferenciaMensajeria.objects.first()
    return pref.connection_id if (pref and pref.connection_id) else "principal"


def _estado_de(sesiones, conn_id: str) -> dict:
    for s in sesiones or []:
        if s.get("connection_id") == conn_id:
            return {
                "connection_id": conn_id,
                "state": s.get("state"),
                "connected": s.get("connected", False),
                "has_qr": s.get("has_qr", False),
            }
    return {"connection_id": conn_id, "state": "sin_sesion", "connected": False, "has_qr": False}


def _passthrough(r, default: dict) -> Response:
    # 5xx del Connector → 502 (bad gateway); el resto se propaga tal cual (200/201/404/409).
    return Response(r.data or default, status=r.status if r.status < 500 else 502)


class WhatsAppSesionView(APIView):
    """GET estado · POST vincular (crea sesión) · DELETE desvincular, de la conexión del tenant."""

    permission_classes = _PERMS

    def get(self, request):
        tenant, conn_id = connection.schema_name, _conn_id()
        try:
            r = solicitar(tenant, "GET", f"/v1/tenants/{tenant}/sessions")
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        sesiones = r.data.get("sessions") if isinstance(r.data, dict) else None
        return Response(_estado_de(sesiones, conn_id))

    def post(self, request):
        tenant, conn_id = connection.schema_name, _conn_id()
        try:
            r = solicitar(
                tenant,
                "POST",
                f"/v1/tenants/{tenant}/sessions",
                {"connection_id": conn_id},
                conn_id,
            )
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        return _passthrough(r, {})

    def delete(self, request):
        tenant, conn_id = connection.schema_name, _conn_id()
        try:
            r = solicitar(
                tenant,
                "POST",
                f"/v1/tenants/{tenant}/sessions/{conn_id}/logout",
                connection_id=conn_id,
            )
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        return _passthrough(r, {"status": "logged_out"})


class WhatsAppQRView(APIView):
    """GET QR (data URL) de la conexión del tenant, para vincular el número."""

    permission_classes = _PERMS

    def get(self, request):
        tenant, conn_id = connection.schema_name, _conn_id()
        try:
            r = solicitar(
                tenant, "GET", f"/v1/tenants/{tenant}/sessions/{conn_id}/qr", connection_id=conn_id
            )
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        return _passthrough(r, {})
