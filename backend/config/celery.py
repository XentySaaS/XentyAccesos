import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("xenty_acceso")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# NOTA (F0): toda tarea que toque modelos TENANT_APPS debe envolverse en
# tenant_context(tenant). Ver CLAUDE.md §4 (Multitenancy).
