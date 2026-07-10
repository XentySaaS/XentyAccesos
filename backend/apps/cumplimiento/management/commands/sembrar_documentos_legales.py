"""Backfill: siembra el aviso de privacidad y los términos por defecto en tenants existentes.

Los tenants nuevos ya nacen con estos documentos (``provisionar_tenant``). Este comando cubre los
tenants creados antes de esa siembra automática. Es **idempotente**: si un tenant ya tiene un tipo de
documento (aunque sea una versión publicada por su admin), no lo toca.

Ejemplos:
  python manage.py sembrar_documentos_legales                # todos los tenants
  python manage.py sembrar_documentos_legales --schema museos
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from apps.cumplimiento.documentos_default import sembrar_documentos_legales


class Command(BaseCommand):
    help = "Siembra los documentos legales por defecto en los tenants existentes que no los tengan."

    def add_arguments(self, parser):
        parser.add_argument("--schema", help="Sembrar solo este tenant (por defecto: todos).")

    def handle(self, *args, **opts):
        publico = get_public_schema_name()
        Tenant = get_tenant_model()
        if opts["schema"]:
            tenants = list(Tenant.objects.filter(schema_name=opts["schema"]))
            if not tenants:
                self.stdout.write(self.style.WARNING(f"No existe el tenant '{opts['schema']}'."))
                return
        else:
            tenants = list(Tenant.objects.exclude(schema_name=publico))

        total = 0
        for tenant in tenants:
            with schema_context(tenant.schema_name):
                creados = sembrar_documentos_legales(tenant.nombre)
            total += creados
            self.stdout.write(f"  {tenant.schema_name}: {creados} documento(s) sembrado(s)")

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Backfill completo: {total} documento(s) en {len(tenants)} tenant(s)."
            )
        )
