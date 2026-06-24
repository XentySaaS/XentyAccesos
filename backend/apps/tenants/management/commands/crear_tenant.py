"""Provisiona un tenant completo: schema + migraciones + usuario admin inicial.

No interactivo y con creación del admin inicial (complementa el ``create_tenant`` interactivo de
django-tenants). Idempotente sobre el schema gracias a ``TenantMixin.auto_create_schema``.

Uso:
    python manage.py crear_tenant <slug> <dominio> --admin-email a@b.mx --admin-nombre "Ada"

Requiere PostgreSQL (django-tenants crea el schema y corre ``migrate_schemas``).
"""
from __future__ import annotations

import secrets

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from apps.accounts.models import Usuario
from apps.tenants.models import Domain, Tenant


class Command(BaseCommand):
    help = "Crea un tenant (schema + migraciones + admin inicial) de forma no interactiva."

    def add_arguments(self, parser):
        parser.add_argument("slug", help="schema_name del tenant (p. ej. 'rayados')")
        parser.add_argument("dominio", help="dominio que resuelve al tenant (p. ej. 'rayados.localhost')")
        parser.add_argument("--nombre", default=None, help="Nombre comercial (default: slug)")
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--admin-nombre", default="Administrador")
        parser.add_argument("--admin-password", default=None, help="Default: aleatoria (se imprime)")

    @transaction.atomic
    def handle(self, *args, **opts):
        slug = opts["slug"].strip().lower()
        if Tenant.objects.filter(schema_name=slug).exists():
            raise CommandError(f"El tenant '{slug}' ya existe.")

        tenant = Tenant.objects.create(schema_name=slug, nombre=opts["nombre"] or slug)
        Domain.objects.create(domain=opts["dominio"], tenant=tenant, is_primary=True)
        self.stdout.write(self.style.SUCCESS(f"✔ Tenant '{slug}' y schema creados."))

        # Migra el schema recién creado (solo este tenant).
        call_command("migrate_schemas", schema_name=slug, interactive=False, verbosity=0)
        self.stdout.write(self.style.SUCCESS("✔ Migraciones aplicadas al schema."))

        password = opts["admin_password"] or secrets.token_urlsafe(12)
        with schema_context(slug):
            Usuario.objects.create_superuser(
                email=opts["admin_email"],
                nombre=opts["admin_nombre"],
                password=password,
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Admin '{opts['admin_email']}' creado."
                + ("" if opts["admin_password"] else f" Password temporal: {password}")
            )
        )
