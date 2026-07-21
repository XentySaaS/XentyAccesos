"""Tareas Celery de configuración: purga de auditoría por retención (multitenant).

Las bitácoras crecen sin límite (``HistorialCambio`` = cambios de datos, ``BitacoraAcceso`` =
accesos al sistema/login). Con varios tenants eso satura el almacenamiento, así que esta purga
borra lo más antiguo que la ventana de retención configurada. Toda operación sobre modelos de
tenant corre dentro de ``schema_context`` (CLAUDE.md §4).

**Configurable en dos niveles:**
- Default global por entorno: ``RETENCION_HISTORIAL_DIAS`` / ``RETENCION_BITACORA_DIAS`` (settings).
- Override por tenant: opciones ``retencion_historial_dias`` / ``retencion_bitacora_dias`` (modelo
  ``Opcion``, editable en ``/api/opciones/``). ``0`` = conservar para siempre (desactiva la purga).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Claves de Opcion (override por tenant) — deben coincidir con lo que edite el admin en /api/opciones/.
RETENCION_HISTORIAL_CLAVE = "retencion_historial_dias"
RETENCION_BITACORA_CLAVE = "retencion_bitacora_dias"


def _dias_retencion(clave: str, default: int) -> int:
    """Días de retención efectivos en el schema activo: opción del tenant o el default global.

    Debe llamarse ya dentro de ``schema_context`` (lee ``Opcion`` del tenant). Un valor inválido
    cae al default; ``0`` (o negativo) significa "conservar para siempre".
    """
    from .models import Opcion

    valor = Opcion.objects.filter(clave=clave).values_list("valor", flat=True).first()
    if valor is None:
        return default
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return default


def _purgar_modelo(modelo, dias: int, *, batch: int, dry_run: bool = False) -> int:
    """Borra (por lotes) las filas de ``modelo`` con ``creado`` anterior a ``dias``.

    ``dias <= 0`` desactiva la purga (devuelve 0). En ``dry_run`` solo cuenta, no borra.
    """
    if dias <= 0:
        return 0
    corte = timezone.now() - timedelta(days=dias)
    antiguos = modelo.objects.filter(creado__lt=corte)
    if dry_run:
        return antiguos.count()
    borrados = 0
    while True:
        # Borrado por lotes para no bloquear la tabla en purgas grandes (muchos tenants/registros).
        ids = list(antiguos.values_list("pk", flat=True)[:batch])
        if not ids:
            break
        modelo.objects.filter(pk__in=ids).delete()
        borrados += len(ids)
    return borrados


def purgar_tenant(schema_name: str, *, dry_run: bool = False) -> dict:
    """Purga las dos bitácoras de un tenant según su retención efectiva. Devuelve conteos."""
    from django_tenants.utils import schema_context

    from .models import BitacoraAcceso, HistorialCambio

    batch = getattr(settings, "RETENCION_PURGA_BATCH", 5000)
    with schema_context(schema_name):
        h_dias = _dias_retencion(RETENCION_HISTORIAL_CLAVE, settings.RETENCION_HISTORIAL_DIAS)
        b_dias = _dias_retencion(RETENCION_BITACORA_CLAVE, settings.RETENCION_BITACORA_DIAS)
        historial = _purgar_modelo(HistorialCambio, h_dias, batch=batch, dry_run=dry_run)
        bitacora = _purgar_modelo(BitacoraAcceso, b_dias, batch=batch, dry_run=dry_run)
    return {
        "schema": schema_name,
        "historial": historial,
        "bitacora": bitacora,
        "historial_dias": h_dias,
        "bitacora_dias": b_dias,
    }


@shared_task
def purgar_bitacoras_todos() -> dict:
    """Purga la auditoría antigua en TODOS los tenants (agendada en Celery beat, diaria).

    Best-effort por tenant: si uno falla, se registra y se continúa con los demás.
    """
    from django_tenants.utils import get_public_schema_name, get_tenant_model

    publico = get_public_schema_name()
    resumen = {"tenants": 0, "historial": 0, "bitacora": 0, "errores": 0}
    for tenant in get_tenant_model().objects.all():
        if tenant.schema_name == publico:
            continue
        resumen["tenants"] += 1
        try:
            r = purgar_tenant(tenant.schema_name)
            resumen["historial"] += r["historial"]
            resumen["bitacora"] += r["bitacora"]
        except Exception as exc:  # noqa: BLE001 — no dejar que un tenant tumbe al resto.
            resumen["errores"] += 1
            logger.warning("Purga de bitácoras falló en tenant %s: %s", tenant.schema_name, exc)
    logger.info("Purga de auditoría por retención: %s", resumen)
    return resumen
