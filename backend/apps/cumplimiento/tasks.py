"""Tareas Celery de cumplimiento (importación EFOS programable, default mensual).

El scheduling (Celery beat) se configura en ops usando ``SAT_EFOS_UPDATE_EVERY_MONTHS``; la tarea
descarga el CSV de ``SAT_EFOS_CSV_URL`` y lo importa dentro del ``tenant_context`` indicado.
"""
from __future__ import annotations

from celery import shared_task
from django.conf import settings

from .services import importar_efos


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def importar_efos_task(self, schema_name: str):
    from django_tenants.utils import schema_context

    if not settings.SAT_EFOS_CSV_URL:
        return {"skipped": "sin SAT_EFOS_CSV_URL"}
    try:
        import requests

        contenido = requests.get(settings.SAT_EFOS_CSV_URL, timeout=60).text
        with schema_context(schema_name):
            return importar_efos(contenido)
    except Exception as exc:
        raise self.retry(exc=exc)
