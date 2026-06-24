"""Ciclo de vida comercial del tenant y ledger de créditos (control plane, schema ``public``).

Centraliza las transiciones de estado (trial → activo → moroso/solo-lectura → suspendido →
cancelado) y la acreditación de créditos. Lo invocan el webhook de Stripe y las acciones del
super-admin. El estado del tenant es lo que después gobiernan los middlewares de enforcement (F0.3).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.tenants.models import (
    MovimientoCredito,
    Plan,
    SaldoCreditos,
    Suscripcion,
    Tenant,
)


def _resolver_plan(meta: dict | None) -> Plan | None:
    """Resuelve el Plan desde la metadata del evento (clave) o cae al primer plan activo."""
    if meta and meta.get("plan"):
        plan = Plan.objects.filter(clave=meta["plan"]).first()
        if plan:
            return plan
    return Plan.objects.filter(activo=True).order_by("id").first()


@transaction.atomic
def activar_suscripcion(tenant: Tenant, *, plan: Plan | None = None,
                        stripe_subscription_id: str | None = None,
                        periodo_inicio=None, periodo_fin=None) -> Suscripcion:
    """Pone el tenant ACTIVO y su suscripción ACTIVA (sale de trial/dunning)."""
    sus = Suscripcion.objects.filter(tenant=tenant).order_by("-id").first()
    plan = plan or (sus.plan if sus else None) or _resolver_plan(None)
    if plan is None:
        raise ValueError("No hay un Plan para activar la suscripción.")
    if sus is None:
        sus = Suscripcion(tenant=tenant, plan=plan)
    sus.plan = plan
    sus.estado = Suscripcion.Estado.ACTIVA
    if stripe_subscription_id:
        sus.stripe_subscription_id = stripe_subscription_id
    if periodo_inicio:
        sus.periodo_inicio = periodo_inicio
    if periodo_fin:
        sus.periodo_fin = periodo_fin
    sus.save()

    tenant.estado = Tenant.Estado.ACTIVO
    tenant.modo_solo_lectura = False
    tenant.save(update_fields=["estado", "modo_solo_lectura"])
    return sus


def marcar_morosa(tenant: Tenant) -> None:
    """Dunning: pago fallido ⇒ suscripción MOROSA + modo solo-lectura (423 en escrituras)."""
    Suscripcion.objects.filter(tenant=tenant).update(estado=Suscripcion.Estado.MOROSA)
    tenant.modo_solo_lectura = True
    tenant.save(update_fields=["modo_solo_lectura"])


def suspender(tenant: Tenant) -> None:
    tenant.estado = Tenant.Estado.SUSPENDIDO
    tenant.save(update_fields=["estado"])


def cancelar(tenant: Tenant) -> None:
    Suscripcion.objects.filter(tenant=tenant).update(estado=Suscripcion.Estado.CANCELADA)
    tenant.estado = Tenant.Estado.CANCELADO
    tenant.save(update_fields=["estado"])


@transaction.atomic
def acreditar_creditos(tenant: Tenant, cantidad: int, motivo: str, referencia: str | None = None) -> int:
    """Suma créditos y registra el movimiento en el ledger append-only. Devuelve el saldo nuevo."""
    saldo, _ = SaldoCreditos.objects.select_for_update().get_or_create(tenant=tenant)
    saldo.saldo += int(cantidad)
    saldo.save(update_fields=["saldo", "actualizado"])
    MovimientoCredito.objects.create(
        tenant=tenant, delta=int(cantidad), motivo=motivo,
        saldo_resultante=saldo.saldo, referencia=referencia,
    )
    return saldo.saldo


# ── Despacho de eventos Stripe → transiciones ───────────────────────────────

def _resolver_tenant(obj: dict) -> Tenant | None:
    meta = obj.get("metadata") or {}
    if meta.get("tenant"):
        t = Tenant.objects.filter(schema_name=meta["tenant"]).first()
        if t:
            return t
    if obj.get("customer"):
        return Tenant.objects.filter(stripe_customer_id=obj["customer"]).first()
    return None


def _aplicar_estado_suscripcion(tenant: Tenant, status: str | None) -> None:
    if status in ("active", "trialing"):
        activar_suscripcion(tenant)
    elif status in ("past_due", "unpaid"):
        marcar_morosa(tenant)
    elif status in ("canceled", "incomplete_expired"):
        cancelar(tenant)


def procesar_evento_stripe(evento: dict) -> dict:
    """Aplica el efecto de un evento Stripe sobre el tenant. Idempotente por naturaleza del estado."""
    tipo = evento.get("type")
    obj = evento.get("data", {}).get("object", {}) or {}
    tenant = _resolver_tenant(obj)
    if tenant is None:
        return {"status": "sin_tenant", "tipo": tipo}

    meta = obj.get("metadata") or {}
    if tipo == "checkout.session.completed":
        if obj.get("mode") == "payment" or meta.get("tipo") == "creditos":
            acreditar_creditos(tenant, int(meta.get("creditos", 0)), "Compra de créditos", obj.get("id"))
        else:
            activar_suscripcion(tenant, plan=_resolver_plan(meta), stripe_subscription_id=obj.get("subscription"))
    elif tipo == "customer.subscription.updated":
        _aplicar_estado_suscripcion(tenant, obj.get("status"))
    elif tipo == "customer.subscription.deleted":
        cancelar(tenant)
    elif tipo == "invoice.payment_failed":
        marcar_morosa(tenant)
    elif tipo == "invoice.payment_succeeded":
        activar_suscripcion(tenant)
    else:
        return {"status": "ignorado", "tipo": tipo, "tenant": tenant.schema_name}

    return {"status": "ok", "tipo": tipo, "tenant": tenant.schema_name}
