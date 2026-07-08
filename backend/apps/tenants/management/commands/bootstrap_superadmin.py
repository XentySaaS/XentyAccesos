"""Auto-siembra el super-admin del control plane al arrancar (idempotente).

Se ejecuta en el arranque del backend en Docker, después de ``bootstrap_public``. Crea el super-admin
SOLO si ``SUPERADMIN_EMAIL`` y ``SUPERADMIN_PASSWORD`` están definidos y aún no existe ninguno. El
super-admin se crea con **MFA obligatorio** (``mfa_habilitado=True``) y sin factor enrolado: el primer
login queda en sesión pendiente hasta que se enrole y verifique el 2º factor (TOTP o passkey).
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.tenants.models import SuperAdmin


class Command(BaseCommand):
    help = "Auto-siembra el super-admin del control plane (env-driven, MFA obligatorio). Idempotente."

    def handle(self, *args, **opts):
        if SuperAdmin.objects.exists():
            self.stdout.write("ℹ Ya existe un super-admin; no se siembra otro.")
            return

        email = (settings.SUPERADMIN_EMAIL or "").strip().lower()
        password = settings.SUPERADMIN_PASSWORD or ""
        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ No se auto-siembra super-admin: define SUPERADMIN_EMAIL y "
                    "SUPERADMIN_PASSWORD en el entorno (o usa `crear_superadmin`)."
                )
            )
            return

        SuperAdmin.objects.create_user(
            email=email,
            nombre=settings.SUPERADMIN_NOMBRE,
            password=password,
            mfa_habilitado=True,  # MFA obligatorio; sin factor enrolado aún
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Super-admin '{email}' creado con MFA obligatorio "
                "(enrola el 2º factor en el primer login)."
            )
        )
