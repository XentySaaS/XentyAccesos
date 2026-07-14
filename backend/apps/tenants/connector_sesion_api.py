"""Gestión de sesiones del XCC por tenant desde el control plane (super-admin).

El super-admin puede vincular/ver/desvincular el WhatsApp de cualquier tenant (soporte / operación
centralizada). Reusa el mismo cliente firmado que el data plane; el tenant y la conexión llegan como
parámetros. Ver `apps.mensajeria.sesion_api` para el equivalente autoservicio del admin del tenant.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mensajeria.connector_client import ConnectorNoDisponible, solicitar
from common.permissions import EsSuperAdmin, MFASesionCompleta

_PERMS = [IsAuthenticated, MFASesionCompleta, EsSuperAdmin]


def _params(request) -> tuple[str, str]:
    tenant = (request.query_params.get("tenant") or request.data.get("tenant") or "").strip()
    conn = (
        request.query_params.get("connection_id")
        or request.data.get("connection_id")
        or "principal"
    ).strip()
    return tenant, conn


def _passthrough(r, default: dict) -> Response:
    return Response(r.data or default, status=r.status if r.status < 500 else 502)


class AdminSesionView(APIView):
    """GET estado (?tenant=&connection_id=) · POST vincular · DELETE desvincular, de cualquier tenant."""

    permission_classes = _PERMS

    def get(self, request):
        tenant, conn = _params(request)
        if not tenant:
            return Response({"detail": "Falta el tenant."}, status=400)
        try:
            r = solicitar(tenant, "GET", f"/v1/tenants/{tenant}/sessions")
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        sesiones = r.data.get("sessions") if isinstance(r.data, dict) else []
        return Response({"tenant": tenant, "connection_id": conn, "sessions": sesiones})

    def post(self, request):
        tenant, conn = _params(request)
        if not tenant:
            return Response({"detail": "Falta el tenant."}, status=400)
        try:
            r = solicitar(
                tenant, "POST", f"/v1/tenants/{tenant}/sessions", {"connection_id": conn}, conn
            )
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        return _passthrough(r, {})

    def delete(self, request):
        tenant, conn = _params(request)
        if not tenant:
            return Response({"detail": "Falta el tenant."}, status=400)
        try:
            r = solicitar(
                tenant, "POST", f"/v1/tenants/{tenant}/sessions/{conn}/logout", connection_id=conn
            )
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        return _passthrough(r, {"status": "logged_out"})


class AdminSesionQRView(APIView):
    """GET QR (data URL) de la conexión de un tenant."""

    permission_classes = _PERMS

    def get(self, request):
        tenant, conn = _params(request)
        if not tenant:
            return Response({"detail": "Falta el tenant."}, status=400)
        try:
            r = solicitar(
                tenant, "GET", f"/v1/tenants/{tenant}/sessions/{conn}/qr", connection_id=conn
            )
        except ConnectorNoDisponible as exc:
            return Response({"detail": str(exc)}, status=503)
        return _passthrough(r, {})
