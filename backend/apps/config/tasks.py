"""Tareas Celery de configuración: purga de auditoría por retención (multitenant).

Las bitácoras crecen sin límite (``HistorialCambio`` = cambios de datos, ``BitacoraAcceso`` =
accesos al sistema/login). Con varios tenants eso satura el almacenamiento, así que esta purga
borra lo más antiguo que la ventana de retención configurada. Toda operación sobre modelos de
tenant corre dentro de ``schema_context`` (CLAUDE.md §4).

**Retención OBLIGATORIA (SaaS por suscripción): entre 1 y 5 meses**, sin opción de "conservar
siempre". Configurable en dos niveles:
- Default global por entorno: ``RETENCION_HISTORIAL_MESES`` / ``RETENCION_BITACORA_MESES``.
- Override por tenant: opciones ``retencion_historial_meses`` / ``retencion_bitacora_meses``
  (modelo ``Opcion``; el admin las edita en *Configuración*). Los valores se acotan a [1, 5] meses.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Claves de Opcion (override por tenant) — deben coincidir con lo que edite el admin en Configuración.
RETENCION_HISTORIAL_CLAVE = "retencion_historial_meses"
RETENCION_BITACORA_CLAVE = "retencion_bitacora_meses"

# Retención obligatoria acotada por suscripción: entre 1 y 5 meses (no hay "conservar siempre").
RETENCION_MESES_MIN = 1
RETENCION_MESES_MAX = 5
DIAS_POR_MES = 30  # aproximación suficiente para una purga de retención


def _meses_retencion(clave: str, default: int) -> int:
    """Meses de retención efectivos en el schema activo, acotados a [MIN, MAX].

    Debe llamarse ya dentro de ``schema_context`` (lee ``Opcion`` del tenant). Un valor inválido
    cae al default; cualquier valor se recorta al rango permitido por la suscripción.
    """
    from .models import Opcion

    valor = Opcion.objects.filter(clave=clave).values_list("valor", flat=True).first()
    n = default
    if valor is not None:
        try:
            n = int(str(valor).strip())
        except (TypeError, ValueError):
            n = default
    return max(RETENCION_MESES_MIN, min(RETENCION_MESES_MAX, n))


def _purgar_modelo(modelo, dias: int, *, batch: int, dry_run: bool = False) -> int:
    """Borra (por lotes) las filas de ``modelo`` con ``creado`` anterior a ``dias``.

    En ``dry_run`` solo cuenta, no borra.
    """
    if dias <= 0:  # defensa: la retención es siempre >= 1 mes, nunca debería entrar aquí.
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
        h_meses = _meses_retencion(RETENCION_HISTORIAL_CLAVE, settings.RETENCION_HISTORIAL_MESES)
        b_meses = _meses_retencion(RETENCION_BITACORA_CLAVE, settings.RETENCION_BITACORA_MESES)
        historial = _purgar_modelo(
            HistorialCambio, h_meses * DIAS_POR_MES, batch=batch, dry_run=dry_run
        )
        bitacora = _purgar_modelo(
            BitacoraAcceso, b_meses * DIAS_POR_MES, batch=batch, dry_run=dry_run
        )
    return {
        "schema": schema_name,
        "historial": historial,
        "bitacora": bitacora,
        "historial_meses": h_meses,
        "bitacora_meses": b_meses,
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
