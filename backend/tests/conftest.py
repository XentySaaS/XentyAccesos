"""Fixtures compartidas de la suite de aislamiento entre tenants (CLAUDE.md §4).

Crear un schema de tenant corre TODAS las migraciones de ``TENANT_APPS`` (costoso). Por eso los
dos tenants de prueba se crean UNA sola vez por módulo (``scope="module"``) y se reutilizan: cada
prueba escribe sus datos DENTRO de un schema vía ``schema_context`` y esos datos se revierten por la
transacción de ``django_db`` de cada test. Los tenants viven fuera de esa transacción (se crean con
``django_db_blocker.unblock``) y se limpian en el teardown del fixture.
"""

import pytest
from django.db import connection


@pytest.fixture(scope="module")
def dos_tenants(django_db_setup, django_db_blocker):
    """Dos tenants reales (schema + migraciones) para verificar aislamiento cruzado.

    Devuelve ``(t1, t2)``. Cada uno tiene su schema PostgreSQL aislado y un dominio primario.
    """
    from apps.tenants.models import Domain, Tenant

    schemas = ["aisl_uno", "aisl_dos"]
    with django_db_blocker.unblock():
        # Limpieza defensiva por si una corrida previa quedó a medias.
        for schema in schemas:
            with connection.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        Tenant.objects.filter(schema_name__in=schemas).delete()

        t1 = Tenant.objects.create(schema_name="aisl_uno", nombre="Tenant Uno")
        Domain.objects.create(domain="aisl-uno.localhost", tenant=t1, is_primary=True)
        t2 = Tenant.objects.create(schema_name="aisl_dos", nombre="Tenant Dos")
        Domain.objects.create(domain="aisl-dos.localhost", tenant=t2, is_primary=True)

        yield t1, t2

        # auto_drop_schema=False (seguridad): el schema se dropea explícitamente aquí.
        for t in (t1, t2):
            with connection.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{t.schema_name}" CASCADE')
            Tenant.objects.filter(pk=t.pk).delete()
