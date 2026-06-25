"""Control plane (schema public): login del super-admin y creación de checkout (F0.5/F0 cierre)."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auth_api import BaseLoginView
from common.permissions import EsSuperAdmin, MFASesionCompleta

from .models import Plan, SuperAdmin, Tenant
from .services.stripe_gateway import crear_checkout_suscripcion


class SuperAdminLoginView(BaseLoginView):
    """POST /api/admin/login/ — autentica al super-admin (MFA si está habilitado)."""

    model = SuperAdmin
    ctx = "superadmin"


class CrearCheckoutView(APIView):
    """POST /api/admin/tenants/<id>/checkout/ — sesión de checkout de suscripción del tenant."""

    permission_classes = [IsAuthenticated, MFASesionCompleta, EsSuperAdmin]

    def post(self, request, tenant_id):
        tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant is None:
            return Response({"detail": "Tenant no encontrado."}, status=404)
        plan = tenant.plan or Plan.objects.filter(activo=True).order_by("id").first()
        if plan is None:
            return Response({"detail": "No hay un plan disponible."}, status=400)
        return Response(crear_checkout_suscripcion(tenant, plan))
