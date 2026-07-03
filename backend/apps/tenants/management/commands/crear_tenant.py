"""Provisiona un tenant completo: schema + migraciones + usuario admin inicial.

No interactivo. Delega en ``apps.tenants.services.provisioning`` (la misma lógica que usa el alta
pública self-service), de modo que CLI y HTTP queden consistentes.

Uso:
    python manage.py crear_tenant <slug> <dominio> --admin-email a@b.mx --admin-nombre "Ada"
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.services.provisioning import ProvisionError, provisionar_tenant


class Command(BaseCommand):
    help = "Crea un tenant (schema + migraciones + admin inicial) de forma no interactiva."

    def add_arguments(self, parser):
        parser.add_argument("slug", help="schema_name del tenant (p. ej. 'rayados')")
        parser.add_argument(
            "dominio", help="dominio que resuelve al tenant (p. ej. 'rayados.localhost')"
        )
        parser.add_argument("--nombre", default=None, help="Nombre comercial (default: slug)")
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--admin-nombre", default="Administrador")
        parser.add_argument(
            "--admin-password", default=None, help="Default: aleatoria (se imprime)"
        )
        parser.add_argument("--plan", default=None, help="clave del plan a asignar")

    def handle(self, *args, **opts):
        try:
            tenant, password = provisionar_tenant(
                slug=opts["slug"],
                dominio=opts["dominio"],
                nombre=opts["nombre"] or opts["slug"],
                admin_email=opts["admin_email"],
                admin_nombre=opts["admin_nombre"],
                admin_password=opts["admin_password"],
                plan_clave=opts["plan"],
            )
        except ProvisionError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"✔ Tenant '{tenant.schema_name}' aprovisionado."))
        if not opts["admin_password"]:
            self.stdout.write(self.style.SUCCESS(f"  Password temporal del admin: {password}"))
