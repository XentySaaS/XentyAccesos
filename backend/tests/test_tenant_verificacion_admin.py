"""Acciones del super-admin para la verificación de correo del admin de un tenant.

Cubre las acciones nuevas de ``TenantAdminViewSet`` (control plane) que operan sobre el ``Usuario``
administrador —que vive en el schema del tenant— cuando el correo de doble opt-in no llegó:
estado, reenviar el correo y verificar manualmente.
"""

import pytest
from django.db import connection
from django_tenants.utils import schema_context
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Usuario
from apps.tenants.admin_api import TenantAdminViewSet
from apps.tenants.models import SuperAdmin

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


def _call(accion, tenant, *, method="post"):
    """Invoca una acción de detalle del viewset como super-admin (sesión MFA completa)."""
    su, _ = SuperAdmin.objects.get_or_create(email="su@xenty.mx", defaults={"nombre": "SU"})
    req = getattr(_factory, method)("/x/")
    force_authenticate(req, user=su, token={"ctx": "superadmin", "mfa": "ok"})
    return TenantAdminViewSet.as_view({method: accion})(req, pk=tenant.pk)


@pytest.fixture(scope="module")
def tenant_sin_verificar(django_db_setup, django_db_blocker):
    """Tenant real cuyo admin queda con el correo SIN verificar (verificar_email=False)."""
    from apps.tenants.models import Tenant
    from apps.tenants.services.provisioning import provisionar_tenant

    slug = "verifqa"
    with django_db_blocker.unblock():
        with connection.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{slug}" CASCADE')
        Tenant.objects.filter(schema_name=slug).delete()

        tenant, _ = provisionar_tenant(
            slug=slug,
            dominio="verifqa.localhost",
            nombre="Verif QA SA",
            admin_email="admin@verifqa.mx",
            admin_nombre="Admin QA",
            verificar_email=False,
        )
        yield tenant

        with connection.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{slug}" CASCADE')
        Tenant.objects.filter(pk=tenant.pk).delete()


def test_verificacion_lista_admin_pendiente(tenant_sin_verificar):
    resp = _call("verificacion", tenant_sin_verificar, method="get")

    assert resp.status_code == 200
    admins = resp.data["administradores"]
    assert len(admins) == 1
    assert admins[0]["email"] == "admin@verifqa.mx"
    assert admins[0]["verificado"] is False


def test_reenviar_verificacion_envia_correo(tenant_sin_verificar, mailoutbox):
    resp = _call("reenviar_verificacion", tenant_sin_verificar)

    assert resp.status_code == 200
    assert resp.data["reenviados"] == ["admin@verifqa.mx"]
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["admin@verifqa.mx"]
    assert mailoutbox[0].alternatives, "El correo lleva la plantilla HTML de marca"


def test_verificar_email_marca_verificado_y_es_idempotente(tenant_sin_verificar):
    resp = _call("verificar_email", tenant_sin_verificar)

    assert resp.status_code == 200
    assert resp.data["verificados"] == ["admin@verifqa.mx"]
    with schema_context(tenant_sin_verificar.schema_name):
        assert Usuario.objects.get(email="admin@verifqa.mx").email_verificado is not None

    # Segunda vez: ya no hay pendientes.
    resp2 = _call("verificar_email", tenant_sin_verificar)
    assert resp2.data["verificados"] == []
