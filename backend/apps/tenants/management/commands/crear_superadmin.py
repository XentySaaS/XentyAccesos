"""Crea (o actualiza) un super-admin del control plane.

Uso: python manage.py crear_superadmin --email root@xenty.mx --nombre Root --password ****
"""

from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand

from apps.tenants.models import SuperAdmin


class Command(BaseCommand):
    help = "Crea un super-admin del control plane."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--nombre", default="Super Admin")
        parser.add_argument("--password", default=None)

    def handle(self, *args, **opts):
        if SuperAdmin.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Ya existe un super-administrador; solo puede haber uno. No se crea otro."
                )
            )
            return
        password = opts["password"] or secrets.token_urlsafe(12)
        SuperAdmin.objects.create_user(
            email=opts["email"], nombre=opts["nombre"], password=password
        )
        self.stdout.write(self.style.SUCCESS(f"✔ Super-admin '{opts['email']}' creado."))
        if not opts["password"]:
            self.stdout.write(self.style.SUCCESS(f"  Password: {password}"))
