"""Pasarela Stripe detrás de interfaz, con MODO SANDBOX automático.

Sandbox (sin ``STRIPE_SECRET_KEY``): no hace llamadas de red ni verifica firmas; simula sesiones de
checkout y acepta el payload del webhook tal cual. Producción (con clave): usa la librería ``stripe``.
Esto permite desarrollar y probar el ciclo de billing completo sin credenciales reales.
"""

from __future__ import annotations

import json

from django.conf import settings


def es_sandbox() -> bool:
    return not bool(settings.STRIPE_SECRET_KEY)


def verificar_webhook(payload: bytes, sig_header: str | None) -> dict:
    """Devuelve el evento como dict. En sandbox no verifica firma; en prod usa el secret de webhook."""
    if es_sandbox() or not settings.STRIPE_WEBHOOK_SECRET:
        return json.loads(payload.decode() if isinstance(payload, bytes) else payload)
    import stripe

    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)


def crear_checkout_suscripcion(tenant, plan) -> dict:
    """Crea (o simula) una sesión de checkout de suscripción para el tenant."""
    if es_sandbox():
        if not tenant.stripe_customer_id:
            tenant.stripe_customer_id = f"cus_sandbox_{tenant.schema_name}"
            tenant.save(update_fields=["stripe_customer_id"])
        return {
            "sandbox": True,
            "tipo": "suscripcion",
            "checkout_url": f"https://sandbox.local/checkout/sub/{tenant.schema_name}",
        }
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    sesion = stripe.checkout.Session.create(
        mode="subscription",
        customer=tenant.stripe_customer_id or None,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        metadata={"tenant": tenant.schema_name, "plan": plan.clave},
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
    )
    return {"sandbox": False, "tipo": "suscripcion", "checkout_url": sesion.url, "id": sesion.id}


def crear_checkout_creditos(tenant, creditos: int, price_id: str | None = None) -> dict:
    """Crea (o simula) una sesión de checkout de compra de un paquete de créditos."""
    if es_sandbox():
        return {
            "sandbox": True,
            "tipo": "creditos",
            "creditos": creditos,
            "checkout_url": f"https://sandbox.local/checkout/cred/{tenant.schema_name}/{creditos}",
        }
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    sesion = stripe.checkout.Session.create(
        mode="payment",
        customer=tenant.stripe_customer_id or None,
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={"tenant": tenant.schema_name, "tipo": "creditos", "creditos": creditos},
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
    )
    return {"sandbox": False, "tipo": "creditos", "checkout_url": sesion.url, "id": sesion.id}
