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


def _config_mesa(tenant):
    from apps.tenants.models import ConfiguracionMesa

    with schema_context(get_public_schema_name()):
        return ConfiguracionMesa.objects.filter(tenant=tenant).first()


def es_sandbox(cfg) -> bool:
    """Sandbox cuando no hay Mesa configurada (sin base_url o deshabilitada): no hace red."""
    return not (cfg and cfg.habilitada and cfg.base_url)


def probar_conexion(tenant) -> dict:
    """Verifica conectividad con la Mesa de Ayuda (Nivel B). Solo lectura; sin datos de dominio."""
    cfg = _config_mesa(tenant)
    if es_sandbox(cfg):
        return {"sandbox": True, "conectado": False,
                "detalle": "Mesa de Ayuda no configurada o deshabilitada."}
    import requests

    try:
        r = requests.get(
            f"{cfg.base_url.rstrip('/')}/health",
            headers={"Authorization": f"Bearer {cfg.api_key}"}, timeout=5,
        )
        return {"sandbox": False, "conectado": r.ok, "status": r.status_code}
    except requests.RequestException as exc:
        return {"sandbox": False, "conectado": False, "detalle": str(exc)}


def enviar_diagnostico(tenant) -> dict:
    """Envía la salud de configuración a la Mesa (solo config, nunca datos de dominio)."""
    cfg = _config_mesa(tenant)
    payload = diagnostico_configuracion(tenant)
    if es_sandbox(cfg):
        return {"sandbox": True, "enviado": False,
                "detalle": "Mesa de Ayuda no configurada.", "diagnostico": payload}
    import requests

    try:
        r = requests.post(
            f"{cfg.base_url.rstrip('/')}/diagnosticos",
            json=payload, headers={"Authorization": f"Bearer {cfg.api_key}"}, timeout=8,
        )
        return {"sandbox": False, "enviado": r.ok, "status": r.status_code}
    except requests.RequestException as exc:
        return {"sandbox": False, "enviado": False, "detalle": str(exc)}


def leer_configuracion(tenant) -> dict:
    """Config de la Mesa para el panel (nunca expone el api_key en claro)."""
    cfg = _config_mesa(tenant)
    return {
        "base_url": cfg.base_url if cfg else "",
        "habilitada": bool(cfg and cfg.habilitada),
        "api_key_configurada": bool(cfg and cfg.api_key),
    }


def guardar_configuracion(tenant, *, base_url=None, habilitada=None, api_key=None) -> dict:
    """Crea/actualiza la config de la Mesa (control plane). ``api_key`` vacío no la borra."""
    from apps.tenants.models import ConfiguracionMesa

    with schema_context(get_public_schema_name()):
        cfg, _ = ConfiguracionMesa.objects.get_or_create(tenant=tenant)
        if base_url is not None:
            cfg.base_url = base_url or None
        if habilitada is not None:
            cfg.habilitada = habilitada
        if api_key:  # solo se actualiza si mandan uno nuevo
            cfg.api_key = api_key
        cfg.save()
    return leer_configuracion(tenant)
