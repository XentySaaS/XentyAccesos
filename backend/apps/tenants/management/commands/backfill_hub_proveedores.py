"""Backfill del hub de proveedores para tenants EXISTENTES (idempotente).

Dos fases por tenant:
1. Crea el ``Domain`` secundario del panel (``<slug>.proveedores.dominio``) si falta.
2. Reconstruye su porción del ``DirectorioProveedor`` (email→tenant) desde las cuentas reales
   del schema — repara cualquier desincronización de las señales (best-effort por diseño).

Los tenants nuevos no lo necesitan: el provisioning crea el dominio y las señales mantienen el
directorio al día.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenants.models import DirectorioProveedor, Domain, Tenant
from apps.tenants.services.provisioning import dominio_panel_proveedores


class Command(BaseCommand):
    help = "Crea dominios del panel de proveedores y reconstruye el directorio email→tenant."

    def handle(self, *args, **opts):
        for tenant in Tenant.objects.exclude(schema_name=get_public_schema_name()):
            # Fase 1: dominio del panel.
            if not Domain.objects.filter(tenant=tenant, es_panel_proveedores=True).exists():
                primario = Domain.objects.filter(tenant=tenant, is_primary=True).first()
                if primario is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ {tenant.schema_name}: sin dominio primario, omitido."
                        )
                    )
                    continue
                dominio = dominio_panel_proveedores(tenant.schema_name, primario.domain)
                Domain.objects.create(
                    domain=dominio, tenant=tenant, is_primary=False, es_panel_proveedores=True
                )
                self.stdout.write(self.style.SUCCESS(f"✔ Dominio panel '{dominio}' creado."))

            # Fase 2: directorio email→tenant (reconstrucción completa de su porción).
            from apps.proveedores.models import CuentaProveedor

            with schema_context(tenant.schema_name):
                cuentas = list(CuentaProveedor.objects.values("id", "email", "activo"))

            vivos: list[int] = []
            for c in cuentas:
                DirectorioProveedor.objects.update_or_create(
                    tenant=tenant,
                    cuenta_id=c["id"],
                    defaults={"email": c["email"].lower(), "activo": c["activo"]},
                )
                vivos.append(c["id"])
            huerfanas, _ = (
                DirectorioProveedor.objects.filter(tenant=tenant)
                .exclude(cuenta_id__in=vivos)
                .delete()
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"✔ {tenant.schema_name}: {len(vivos)} cuenta(s) en directorio"
                    + (f", {huerfanas} huérfana(s) eliminada(s)." if huerfanas else ".")
                )
            )
