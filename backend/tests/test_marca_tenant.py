"""El tenant (p. ej. «3 Museos») es quien invita/notifica: aparece como remitente en el correo y en
la firma, en vez de «Xenty Accesos» o del schema técnico «museos».
"""

from __future__ import annotations

import pytest
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def test_nombre_tenant_actual_resuelve_display(dos_tenants):
    """Bajo schema_context (FakeTenant sin ``nombre``) el helper resuelve el nombre display real."""
    from common.tenant import nombre_tenant_actual

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        assert nombre_tenant_actual() == "Tenant Uno"  # no «aisl_uno»


def test_nombre_tenant_actual_default_en_public():
    from common.tenant import nombre_tenant_actual

    # Sin tenant (schema público / control plane) → cae al default.
    assert nombre_tenant_actual(default="Xenty Accesos") == "Xenty Accesos"


def test_header_muestra_al_tenant_como_emisor():
    from common.email_builder import construir_correo

    html = construir_correo(
        nombre_tenant="3 Museos",
        asunto="Prueba",
        titulo="Prueba",
        mensaje="Contenido",
        filas=[{"label": "A", "valor": "B"}],
    )
    assert "3 Museos" in html  # el tenant es el remitente visible en el encabezado


def test_firma_plana_termina_en_el_tenant_sin_xenty():
    from common.emails import _plano

    txt = _plano("Hola,", ["cuerpo"], url=None, nombre_tenant="3 Museos")
    assert txt.strip().endswith("— 3 Museos")
    assert "Xenty" not in txt  # la firma ya no arrastra «· Xenty Acceso»


def test_endpoint_publico_marca_devuelve_nombre_del_tenant(dos_tenants):
    """GET /api/publico/marca/ (data plane): nombre display del tenant del host, sin auth."""
    from common.tenant import MarcaTenantView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r = MarcaTenantView().get(None)
    assert r.status_code == 200 and r.data == {"nombre": "Tenant Uno"}
