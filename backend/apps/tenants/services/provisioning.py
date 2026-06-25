"""Aprovisionamiento de un tenant completo (lo usan el CLI y el alta pública self-service).

Crea Tenant + schema (auto-migrado por django-tenants) + Domain + SaldoCreditos + trial + usuario
administrador inicial, todo de forma atómica.
"""
from __future__ import annotations

import re
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.tenants.models import Domain, Plan, SaldoCreditos, Tenant

_SLUG_RE = re.compile(r"^[a-z][a-z0-9]{2,30}$")
TRIAL_DIAS = 14


class ProvisionError(ValueError):
    pass


def provisionar_tenant(
    *, slug: str, dominio: str, nombre: str, admin_email: str, admin_nombre: str,
    admin_password: str | None = None, plan_clave: str | None = None, trial_dias: int = TRIAL_DIAS,
):
    """Aprovisiona el tenant y su admin. Devuelve ``(tenant, password)``."""
    slug = slug.strip().lower()
    if not _SLUG_RE.match(slug):
        raise ProvisionError("Subdominio inválido (3-31 chars, [a-z0-9], inicia con letra).")
    if Tenant.objects.filter(schema_name=slug).exists():
        raise ProvisionError(f"El subdominio '{slug}' ya está en uso.")
    if Domain.objects.filter(domain=dominio).exists():
        raise ProvisionError(f"El dominio '{dominio}' ya está en uso.")

    plan = (
        Plan.objects.filter(clave=plan_clave).first() if plan_clave else None
    ) or Plan.objects.filter(activo=True).order_by("id").first()

    with transaction.atomic():
        tenant = Tenant.objects.create(  # auto_create_schema migra el schema al guardar
            schema_name=slug, nombre=nombre, plan=plan,
            estado=Tenant.Estado.TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=trial_dias),
        )
        Domain.objects.create(domain=dominio, tenant=tenant, is_primary=True)
        SaldoCreditos.objects.get_or_create(tenant=tenant, defaults={"saldo": 0})

    password = admin_password or secrets.token_urlsafe(12)
    from apps.accounts.models import Usuario

    with schema_context(slug):
        Usuario.objects.create_superuser(email=admin_email, nombre=admin_nombre, password=password)

    return tenant, password
