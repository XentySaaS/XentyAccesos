"""Tareas Celery de mensajería. Toda tarea con modelos de tenant corre en ``tenant_context``."""
from __future__ import annotations

from celery import shared_task

from .services import procesar_envio


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def enviar_campana(self, schema_name: str, mensaje_id: int):
    """Procesa el envío de una campaña dentro del contexto del tenant (CLAUDE.md §4)."""
    from django_tenants.utils import schema_context

    try:
        with schema_context(schema_name):
            return procesar_envio(mensaje_id)
    except Exception as exc:  # reintento con backoff
        raise self.retry(exc=exc)
