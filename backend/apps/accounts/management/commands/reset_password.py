"""Resetea la contraseña de un usuario (acceso) en el schema del tenant indicado.

Uso:
    python manage.py reset_password --schema=rayados --email=admin@empresa.com --password=NuevaClave
    python manage.py reset_password --schema=rayados --email=admin@empresa.com   # genera contraseña aleatoria
"""

from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = "Resetea la contraseña de un usuario (contexto acceso) en el tenant indicado."

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True, help="Slug del tenant (ej: rayados)")
        parser.add_argument("--email", required=True, help="Email del usuario")
        parser.add_argument(
            "--password", required=False, help="Nueva contraseña (vacío = genera aleatoria)"
        )

    def handle(self, *args, **opts):
        schema = opts["schema"].strip().lower()
        email = opts["email"].strip().lower()
        password = opts.get("password") or secrets.token_urlsafe(12)

        try:
            with schema_context(schema):
                from apps.accounts.models import Usuario

                try:
                    user = Usuario.objects.get(email=email)
                except Usuario.DoesNotExist:
                    raise CommandError(f"Usuario '{email}' no encontrado en schema '{schema}'.")
                user.set_password(password)
                user.save(update_fields=["password"])
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f"Error al resetear contraseña: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(f"✔ Contraseña actualizada para {email} en schema '{schema}'.")
        )
        if not opts.get("password"):
            self.stdout.write(self.style.WARNING(f"   Contraseña generada: {password}"))
