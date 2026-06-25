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

    def handle(self, *args, **opts):
        base = getattr(settings, "TENANT_BASE_DOMAIN", "localhost")
        # Hosts que sirve el control plane (LP, www y panel super-admin) → schema public.
        hosts = [base, f"www.{base}", f"xenty.{base}", f"admin.{base}"]

        tenant = Tenant.objects.filter(schema_name="public").first()
        if tenant is None:
            tenant = Tenant(schema_name="public", nombre="Public", estado=Tenant.Estado.ACTIVO)
            tenant.auto_create_schema = False  # el schema 'public' ya existe
            tenant.save()
            self.stdout.write(self.style.SUCCESS("✔ Tenant público creado."))

        for i, host in enumerate(hosts):
            _, creado = Domain.objects.get_or_create(
                domain=host, tenant=tenant, defaults={"is_primary": i == 0}
            )
            self.stdout.write(self.style.SUCCESS(f"✔ Dominio público '{host}' {'creado' if creado else 'ya existía'}."))
