"""Suscripción del tenant — vista AUTOSERVICIO (data plane, admin del tenant).

Distinta de ``admin_api`` (control plane, super-admin). Aquí el admin del propio tenant ve su
suscripción y puede **cancelar la cuenta** desde la zona peligrosa. Cancelar es la baja comercial
suave (``billing.cancelar``): marca la suscripción CANCELADA y el tenant CANCELADO (el middleware
lo bloquea), **conservando los datos**; el super-admin puede reactivar o purgar después. No se
dropea el schema (``auto_drop_schema=False``).
"""

from __future__ import annotations

from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereRol

from .models import Suscripcion, Tenant
from .services import billing

_ADMIN = [*PERMISOS_BASE(), ContextoAcceso, RequiereRol("administrador")]


def _tenant_actual() -> Tenant | None:
    """Tenant del schema activo; ``None`` en el schema público (no aplica)."""
    t = getattr(connection, "tenant", None)
    if t is None or getattr(t, "schema_name", None) in (None, "public"):
        return None
    # ``connection.tenant`` puede ser un FakeTenant; resolvemos el modelo real por schema.
    if isinstance(t, Tenant):
        return t
    return Tenant.objects.filter(schema_name=t.schema_name).first()


def _resumen(tenant: Tenant) -> dict:
    plan = tenant.plan
    sus = Suscripcion.objects.filter(tenant=tenant).order_by("-creado").first()
    return {
        "tenant": {
            "nombre": tenant.nombre,
            "estado": tenant.estado,
            "estado_label": Tenant.Estado(tenant.estado).label,
            "trial_ends_at": tenant.trial_ends_at,
            "gracia_hasta": tenant.gracia_hasta,
        },
        "plan": (
            {
                "nombre": plan.nombre,
                "descripcion": plan.descripcion,
                "precio_mensual": str(plan.precio_mensual),
                "modulos": plan.modulos or [],
            }
            if plan
            else None
        ),
        "suscripcion": (
            {
                "estado": sus.estado,
                "estado_label": Suscripcion.Estado(sus.estado).label,
                "periodo_fin": sus.periodo_fin,
                "cancelar_al_fin_periodo": sus.cancelar_al_fin_periodo,
            }
            if sus
            else None
        ),
    }


class SuscripcionTenantView(APIView):
    """GET → suscripción del tenant actual · POST → cancelar la cuenta (zona peligrosa)."""

    permission_classes = _ADMIN

    def get(self, request):
        tenant = _tenant_actual()
        if tenant is None:
            return Response({"detail": "Sin tenant en contexto."}, status=400)
        return Response(_resumen(tenant))

    def post(self, request):
        tenant = _tenant_actual()
        if tenant is None:
            return Response({"detail": "Sin tenant en contexto."}, status=400)
        if tenant.estado == Tenant.Estado.CANCELADO:
            return Response({"detail": "La cuenta ya está cancelada."}, status=409)

        # Confirmación fuerte: hay que escribir el nombre exacto de la cuenta (estilo "danger zone").
        confirmacion = str((request.data or {}).get("confirmacion", "")).strip()
        if confirmacion.casefold() != tenant.nombre.strip().casefold():
            return Response(
                {"detail": "La confirmación no coincide con el nombre de la cuenta."}, status=400
            )

        billing.cancelar(tenant)  # baja suave: suscripción CANCELADA + tenant CANCELADO
        _auditar_cancelacion(request, tenant)
        tenant.refresh_from_db()
        return Response(_resumen(tenant))


def _auditar_cancelacion(request, tenant: Tenant) -> None:
    """Deja constancia en el HistorialCambio del tenant (best-effort)."""
    try:
        from apps.config.models import HistorialCambio

        actor = getattr(request, "user", None)
        HistorialCambio.objects.create(
            descripcion=f"Cuenta cancelada por el administrador ({getattr(actor, 'email', '—')}).",
            modelo="tenants.Tenant",
            accion=HistorialCambio.Accion.ELIMINADO,
            usuario=actor if getattr(actor, "is_authenticated", False) else None,
        )
    except Exception:  # noqa: BLE001 — la auditoría nunca debe tumbar la acción
        pass
