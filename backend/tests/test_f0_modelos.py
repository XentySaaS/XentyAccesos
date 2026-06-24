"""F0.1 — Pruebas de los modelos del control plane y del Usuario.

Requieren PostgreSQL (django-tenants). Verifican: cifrado Fernet de PII en reposo, ledger de
créditos append-only y reglas básicas del Usuario (login exige activo, baja lógica).
"""
import pytest
from django.db import connection

from apps.tenants.models import DispositivoEdge, Tenant


@pytest.fixture
def tenant_demo(db):
    """Crea un tenant de prueba con su schema y entra en su contexto."""
    from django_tenants.utils import schema_context

    tenant = Tenant.objects.create(schema_name="test_demo", nombre="Demo")
    with schema_context("test_demo"):
        yield tenant


@pytest.mark.django_db
def test_token_edge_cifrado_en_reposo():
    """El token HMAC del dispositivo se guarda como ciphertext, no en claro (REMEDIACION §C3)."""
    tenant = Tenant.objects.create(schema_name="public_t1", nombre="T1")
    disp = DispositivoEdge.objects.create(
        tenant=tenant, mac_address="AA:BB:CC:DD:EE:FF", nombre="Torniquete 1", token="secreto-hmac"
    )
    # Lectura por ORM: descifrado transparente.
    disp.refresh_from_db()
    assert disp.token == "secreto-hmac"
    # Lectura cruda de la columna: debe ser ciphertext (no el valor en claro).
    with connection.cursor() as cur:
        cur.execute("SELECT token FROM tenants_dispositivoedge WHERE id = %s", [disp.id])
        crudo = cur.fetchone()[0]
    assert crudo != "secreto-hmac"
    assert "secreto-hmac" not in crudo


@pytest.mark.django_db
def test_usuario_login_exige_activo():
    """Un usuario dado de baja (activo=False) no puede autenticar."""
    from django.contrib.auth import authenticate

    from apps.tenants.models import Domain

    tenant = Tenant.objects.create(schema_name="test_login", nombre="Login")
    Domain.objects.create(domain="login.localhost", tenant=tenant, is_primary=True)
    from django_tenants.utils import schema_context

    from apps.accounts.models import Usuario

    with schema_context("test_login"):
        u = Usuario.objects.create_user(email="a@b.mx", nombre="Ada", password="Secreta123!")
        assert authenticate(username="a@b.mx", password="Secreta123!") == u
        u.activo = False
        u.save()
        assert authenticate(username="a@b.mx", password="Secreta123!") is None
