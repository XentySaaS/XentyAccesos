import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("xenty_acceso")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Actualización AUTOMÁTICA del padrón SAT 69-B: el sistema la corre solo (los admins del tenant
# no programan ni importan nada). Cada mes, día 1 a las 03:00, descarga el CSV del SAT una vez y
# lo importa + revalida en todos los tenants. El intervalo mensual coincide con el ritmo real de
# publicación del SAT; la auto-reparación diferida (al abrir Cumplimiento con padrón vacío) cubre
# a los tenants nuevos entre corridas.
app.conf.beat_schedule = {
    "sincronizar-efos-69b-mensual": {
        "task": "apps.cumplimiento.tasks.sincronizar_efos_todos",
        "schedule": crontab(day_of_month="1", hour="3", minute="0"),
    },
    # Purga diaria de auditoría (historial de cambios + accesos al sistema) por retención, en todos
    # los tenants, para no saturar el almacenamiento al escalar. La ventana es configurable por
    # entorno (RETENCION_*_DIAS) y por tenant (opciones retencion_*_dias); 0 = conservar siempre.
    "purgar-bitacoras-diaria": {
        "task": "apps.config.tasks.purgar_bitacoras_todos",
        "schedule": crontab(hour="3", minute="30"),
    },
}

# NOTA (F0): toda tarea que toque modelos TENANT_APPS debe envolverse en
# tenant_context(tenant). Ver CLAUDE.md §4 (Multitenancy).
