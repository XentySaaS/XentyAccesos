"""Crea el tenant PÚBLICO y su dominio (idempotente).

django-tenants necesita un Tenant con ``schema_name='public'`` y un Domain para rutear el control
plane y cualquier petición al dominio base. Se ejecuta al arrancar el backend en Docker.
"""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.tenants.models import Domain, Tenant


class Command(BaseCommand):
    help = "Crea el tenant público (schema 'public') y su dominio base. Idempotente."

    def add_arguments(self, parser):
        parser.add_argument("--dominio", default=getattr(settings, "TENANT_BASE_DOMAIN", "localhost"))

    def handle(self, *args, **opts):
        tenant = Tenant.objects.filter(schema_name="public").first()
        if tenant is None:
            tenant = Tenant(schema_name="public", nombre="Public", estado=Tenant.Estado.ACTIVO)
            tenant.auto_create_schema = False  # el schema 'public' ya existe
            tenant.save()
            self.stdout.write(self.style.SUCCESS("✔ Tenant público creado."))
        _, creado = Domain.objects.get_or_create(
            domain=opts["dominio"], tenant=tenant, defaults={"is_primary": True}
        )
        self.stdout.write(self.style.SUCCESS(f"✔ Dominio público '{opts['dominio']}' {'creado' if creado else 'ya existía'}."))
