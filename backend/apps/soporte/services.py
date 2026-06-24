"""Cliente de Mesa de Ayuda (Nivel B): SOLO lee salud de configuración para diagnóstico.

Nunca ejecuta cómputo de dominio ni consume créditos (CLAUDE.md §9). Útil para que soporte
diagnostique un tenant sin tocar sus datos operativos.
"""
from __future__ import annotations

from django.conf import settings
from django_tenants.utils import get_public_schema_name, schema_context


def diagnostico_configuracion(tenant) -> dict:
    """Devuelve un resumen de salud de configuración del tenant (solo lectura)."""
    from apps.tenants.models import ConfiguracionMesa

    with schema_context(get_public_schema_name()):
        cfg = ConfiguracionMesa.objects.filter(tenant=tenant).first()
        mesa_habilitada = bool(cfg and cfg.habilitada)
        plan = tenant.plan.clave if tenant.plan_id else None
        estado = tenant.estado

    return {
        "tenant": tenant.schema_name,
        "estado": estado,
        "plan": plan,
        "modo_solo_lectura": tenant.modo_solo_lectura,
        "cifrado_fernet_configurado": bool(settings.SECRET_KEY_FERNET),
        "stripe_modo": "sandbox" if not settings.STRIPE_SECRET_KEY else "live",
        "mesa_ayuda_habilitada": mesa_habilitada,
        "email_configurado": bool(getattr(settings, "EMAIL_HOST", "")),
        "debug": settings.DEBUG,
    }
