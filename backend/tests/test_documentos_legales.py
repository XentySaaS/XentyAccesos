"""Siembra automática de documentos legales (aviso de privacidad + términos) al crear un tenant.

Verifica el sembrador (``apps.cumplimiento.documentos_default``) de forma directa sobre un schema de
tenant y su integración real con ``provisionar_tenant``.
"""

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.cumplimiento.documentos_default import sembrar_documentos_legales
from apps.cumplimiento.models import DocumentoLegal

pytestmark = pytest.mark.django_db


# ── Sembrador directo ────────────────────────────────────────────────────────
def test_siembra_crea_aviso_y_terminos_v1(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        creados = sembrar_documentos_legales("Rayados SA de CV")

        assert creados == 2
        tipos = set(DocumentoLegal.objects.values_list("tipo", flat=True))
        assert tipos == {"aviso_privacidad", "terminos_condiciones"}
        for doc in DocumentoLegal.objects.all():
            assert doc.version == 1
            assert doc.texto.strip(), "El texto no puede quedar vacío"
            assert "Rayados SA de CV" in doc.texto, "El nombre del tenant debe interpolarse"


def test_siembra_es_idempotente(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        assert sembrar_documentos_legales("Acme SA") == 2
        assert sembrar_documentos_legales("Acme SA") == 0, "La 2ª siembra no debe crear nada"
        assert DocumentoLegal.objects.count() == 2, "No debe duplicar ni crear v2"


def test_siembra_respeta_documento_ya_publicado(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        # El admin ya publicó su propio aviso: la siembra no debe pisarlo.
        DocumentoLegal.objects.create(
            tipo=DocumentoLegal.Tipo.AVISO_PRIVACIDAD, texto="Mi aviso propio", version=1
        )
        creados = sembrar_documentos_legales("Acme SA")

        assert creados == 1, "Solo debe sembrar los términos (el aviso ya existía)"
        aviso = DocumentoLegal.objects.get(tipo=DocumentoLegal.Tipo.AVISO_PRIVACIDAD)
        assert aviso.texto == "Mi aviso propio"


# ── Integración con el provisioning ──────────────────────────────────────────
@pytest.fixture(scope="module")
def tenant_provisionado(django_db_setup, django_db_blocker):
    """Aprovisiona un tenant real (schema + migraciones) vía ``provisionar_tenant`` y lo limpia.

    Igual que ``dos_tenants``, vive fuera de la transacción de ``django_db`` (crear un schema corre
    migraciones), por eso se crea con ``unblock`` y se dropea explícitamente en el teardown.
    """
    from apps.tenants.models import Tenant
    from apps.tenants.services.provisioning import provisionar_tenant

    slug = "provdocs"
    with django_db_blocker.unblock():
        with connection.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{slug}" CASCADE')
        Tenant.objects.filter(schema_name=slug).delete()

        tenant, _ = provisionar_tenant(
            slug=slug,
            dominio="provdocs.localhost",
            nombre="Provisionado SA",
            admin_email="admin@provdocs.mx",
            admin_nombre="Admin",
        )
        yield tenant

        with connection.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{slug}" CASCADE')
        Tenant.objects.filter(pk=tenant.pk).delete()


def test_provisionar_tenant_siembra_los_documentos(tenant_provisionado):
    with schema_context(tenant_provisionado.schema_name):
        docs = {d.tipo: d for d in DocumentoLegal.objects.all()}
        assert set(docs) == {"aviso_privacidad", "terminos_condiciones"}
        assert all(d.version == 1 for d in docs.values())
        assert "Provisionado SA" in docs["aviso_privacidad"].texto
