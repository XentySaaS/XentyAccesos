"""Importa el CSV oficial SAT 69-B (EFOS) al espejo del tenant indicado.

Uso: python manage.py importar_efos --schema <slug> --archivo lista69b.csv
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from apps.cumplimiento.services import importar_efos


class Command(BaseCommand):
    help = "Importa el CSV de EFOS (SAT 69-B) al espejo del tenant."

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True)
        parser.add_argument("--archivo", required=True)

    def handle(self, *args, **opts):
        try:
            with open(opts["archivo"], encoding="utf-8") as f:
                contenido = f.read()
        except OSError as exc:
            raise CommandError(str(exc))
        with schema_context(opts["schema"]):
            res = importar_efos(contenido)
        self.stdout.write(self.style.SUCCESS(f"EFOS importados: {res}"))
