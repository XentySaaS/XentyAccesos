"""Purga manual de auditoría por retención (equivalente CLI de la tarea Celery diaria).

Útil para operar/verificar sin esperar al beat. Ejemplos:
    python manage.py purgar_bitacoras --dry-run           # todos los tenants, solo cuenta
    python manage.py purgar_bitacoras --schema=museos      # un tenant, borra
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Purga HistorialCambio y BitacoraAcceso más antiguos que la retención configurada."

    def add_arguments(self, parser):
        parser.add_argument("--schema", help="Solo este tenant (schema_name). Por defecto: todos.")
        parser.add_argument(
            "--dry-run", action="store_true", help="Solo cuenta lo que se borraría; no borra."
        )

    def handle(self, *args, **opts):
        from django_tenants.utils import get_public_schema_name, get_tenant_model

        from apps.config.tasks import purgar_tenant

        dry = opts["dry_run"]
        publico = get_public_schema_name()
        if opts.get("schema"):
            schemas = [opts["schema"]]
        else:
            schemas = [
                t.schema_name for t in get_tenant_model().objects.all() if t.schema_name != publico
            ]

        verbo = "se borrarían" if dry else "borrados"
        for schema in schemas:
            r = purgar_tenant(schema, dry_run=dry)
            self.stdout.write(
                f"{schema}: historial {verbo} {r['historial']} (retención {r['historial_meses']} mes(es)), "
                f"bitácora {verbo} {r['bitacora']} (retención {r['bitacora_meses']} mes(es))"
            )
        self.stdout.write(self.style.SUCCESS(f"Listo ({len(schemas)} tenant(s))."))
