"""Tareas Celery de cumplimiento: actualización AUTOMÁTICA del padrón 69-B.

Los admins del tenant son usuarios casi finales: no deben importar ni programar nada a mano.
``sincronizar_efos_todos`` (agendada en Celery beat, ver config/celery.py) descarga el CSV público
del SAT UNA vez y lo importa + revalida en cada tenant. ``importar_efos_task`` cubre un solo tenant
(p. ej. auto-reparación diferida cuando un tenant abre Cumplimiento con el padrón vacío).
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from .services import importar_efos, revalidar_todos

logger = logging.getLogger(__name__)

_SAT_URL_DEFAULT = "http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv"


def _descargar_csv() -> bytes:
    """Descarga el CSV del SAT como bytes (la decodificación la hace el importador)."""
    import requests

    url = settings.SAT_EFOS_CSV_URL or _SAT_URL_DEFAULT
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def importar_efos_task(self, schema_name: str):
    """Importa + revalida el padrón para UN tenant. Descarga el CSV del SAT."""
    from django_tenants.utils import schema_context

    try:
        contenido = _descargar_csv()
        with schema_context(schema_name):
            res = importar_efos(contenido)
            rev = revalidar_todos()
        return {"schema": schema_name, **res, "encontrados": rev["encontrados"]}
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=900)
def sincronizar_efos_todos(self):
    """Descarga el CSV del SAT una sola vez y lo importa + revalida en cada tenant.

    Best-effort por tenant: si uno falla, se registra y se continúa con los demás.
    """
    from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

    try:
        contenido = _descargar_csv()
    except Exception as exc:  # noqa: BLE001 — sin CSV no hay nada que hacer; reintenta la tarea.
        raise self.retry(exc=exc)

    publico = get_public_schema_name()
    resumen = {"tenants": 0, "ok": 0, "errores": 0}
    for tenant in get_tenant_model().objects.all():
        if tenant.schema_name == publico:
            continue
        resumen["tenants"] += 1
        try:
            with schema_context(tenant.schema_name):
                importar_efos(contenido)
                revalidar_todos()
            resumen["ok"] += 1
        except Exception as exc:  # noqa: BLE001 — no dejar que un tenant tumbe al resto.
            resumen["errores"] += 1
            logger.warning("EFOS no sincronizado en tenant %s: %s", tenant.schema_name, exc)
    logger.info("Sincronización EFOS 69-B: %s", resumen)
    return resumen
