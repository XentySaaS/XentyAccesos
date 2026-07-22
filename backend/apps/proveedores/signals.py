"""Sincroniza el DirectorioProveedor global (schema public) con las cuentas del tenant.

El hub de login de proveedores (``proveedores.dominio``) necesita saber en qué tenants existe un
correo SIN escanear schemas. Estas señales mantienen ese índice al día en cada alta, cambio de
email, baja lógica o borrado de ``CuentaProveedor``. Son best-effort: un fallo al escribir en
public no debe romper la operación del tenant (el comando ``backfill_hub_proveedores`` repara).
"""

from __future__ import annotations

import structlog
from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_tenants.utils import get_public_schema_name

from .models import CuentaProveedor

log = structlog.get_logger(__name__)


def _tenant_actual():
    """Tenant dueño del schema activo, o None si estamos en public (no aplica)."""
    from apps.tenants.models import Tenant

    schema = connection.schema_name
    if schema == get_public_schema_name():
        return None
    return Tenant.objects.filter(schema_name=schema).first()


@receiver(post_save, sender=CuentaProveedor, dispatch_uid="directorio-proveedor-upsert")
def actualizar_directorio(sender, instance: CuentaProveedor, **kwargs) -> None:
    tenant = _tenant_actual()
    if tenant is None:
        return
    try:
        from apps.tenants.models import DirectorioProveedor

        DirectorioProveedor.objects.update_or_create(
            tenant=tenant,
            cuenta_id=instance.pk,
            defaults={"email": (instance.email or "").lower(), "activo": instance.activo},
        )
    except Exception:  # noqa: BLE001 — best-effort: nunca romper la operación del tenant
        log.warning(
            "directorio_proveedor_upsert_fallo", tenant=tenant.schema_name, cuenta=instance.pk
        )


@receiver(post_delete, sender=CuentaProveedor, dispatch_uid="directorio-proveedor-delete")
def retirar_del_directorio(sender, instance: CuentaProveedor, **kwargs) -> None:
    tenant = _tenant_actual()
    if tenant is None:
        return
    try:
        from apps.tenants.models import DirectorioProveedor

        DirectorioProveedor.objects.filter(tenant=tenant, cuenta_id=instance.pk).delete()
    except Exception:  # noqa: BLE001
        log.warning(
            "directorio_proveedor_delete_fallo", tenant=tenant.schema_name, cuenta=instance.pk
        )
