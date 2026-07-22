"""Hub de login de proveedores: dominio del panel, directorio global y flujo de verificación.

Las vistas se invocan directamente (sin la pila de URLs del control plane), como en
``test_backup_codes``. El rate limit se desactiva (feature del framework, no lo probado aquí).
El correo usa el backend locmem de pytest-django (``mailoutbox``).
"""

from __future__ import annotations

import re
from uuid import uuid4

import pytest
from django_tenants.utils import schema_context
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


def _req(data: dict, cookies: dict | None = None) -> Request:
    crudo = _factory.post("/x/", data, format="json")
    if cookies:
        crudo.COOKIES.update(cookies)
    return Request(crudo, parsers=[JSONParser()])


def _cuenta(email: str):
    from apps.proveedores.models import CuentaProveedor

    return CuentaProveedor.objects.create_user(email=email, nombre="Resp", password="secreta")


def _email_unico(prefijo: str) -> str:
    """Correo único por corrida: el cooldown de envío vive en Redis y sobrevive entre corridas."""
    return f"{prefijo}-{uuid4().hex[:8]}@empresa.com"


# ── Dominio del panel ────────────────────────────────────────────────────────
def test_dominio_panel_proveedores():
    from apps.tenants.services.provisioning import dominio_panel_proveedores

    assert dominio_panel_proveedores("museos", "museos.localhost") == "museos.proveedores.localhost"
    assert dominio_panel_proveedores("acme", "acme.xenty.mx") == "acme.proveedores.xenty.mx"
    # Dominio primario atípico (no empieza con el slug): cuelga del dominio base configurado.
    assert dominio_panel_proveedores("acme", "portal-acme.com").startswith("acme.proveedores.")


def test_url_panel_proveedores_desde_request(dos_tenants):
    from apps.tenants.models import Domain
    from common.panel_proveedores import url_panel_proveedores

    t1, _ = dos_tenants
    peticion = _factory.get("/", HTTP_HOST="aisl-uno.localhost:8080")

    # Sin registro Domain: fallback textual '<slug>.dominio' → '<slug>.proveedores.dominio'.
    assert (
        url_panel_proveedores(peticion, tenant=None) == "http://aisl-uno.proveedores.localhost:8080"
    )

    # El hub es transversal: siempre proveedores.<dominio base> con esquema/puerto de la petición.
    from common.panel_proveedores import url_hub_proveedores

    assert url_hub_proveedores(peticion) == "http://proveedores.localhost:8080"

    # Con registro Domain del panel: manda la tabla (fuente de verdad).
    Domain.objects.create(
        domain="aisl-uno.proveedores.localhost",
        tenant=t1,
        is_primary=False,
        es_panel_proveedores=True,
    )
    try:
        assert (
            url_panel_proveedores(peticion, tenant=t1)
            == "http://aisl-uno.proveedores.localhost:8080"
        )
        # Si la petición YA llega al host del panel (p. ej. reset), se conserva tal cual.
        en_panel = _factory.get("/", HTTP_HOST="aisl-uno.proveedores.localhost:8080")
        assert (
            url_panel_proveedores(en_panel, tenant=None)
            == "http://aisl-uno.proveedores.localhost:8080"
        )
    finally:
        Domain.objects.filter(tenant=t1, es_panel_proveedores=True).delete()


# ── Directorio global (señales) ──────────────────────────────────────────────
def test_directorio_se_sincroniza_con_senales(dos_tenants):
    from apps.tenants.models import DirectorioProveedor

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cuenta = _cuenta("Sync@Empresa.com")

        entrada = DirectorioProveedor.objects.get(tenant=t1, cuenta_id=cuenta.pk)
        assert entrada.email == "sync@empresa.com"  # normalizado en minúsculas
        assert entrada.activo is True

        cuenta.email = "nuevo@empresa.com"
        cuenta.save(update_fields=["email"])
        entrada.refresh_from_db()
        assert entrada.email == "nuevo@empresa.com"

        cuenta.activo = False
        cuenta.save(update_fields=["activo"])
        entrada.refresh_from_db()
        assert entrada.activo is False

        cuenta.delete()
        assert not DirectorioProveedor.objects.filter(tenant=t1, cuenta_id=cuenta.pk).exists()


# ── Flujo del hub (código + cookie de dispositivo; membresía por-tenant protegida) ──
def test_hub_no_enumera_y_verifica_por_codigo(dos_tenants, settings, mailoutbox):
    from apps.tenants.hub_proveedores_api import (
        COOKIE_DISPOSITIVO,
        EspaciosProveedorView,
        VerificarEspaciosView,
    )
    from apps.tenants.models import Domain

    settings.RATELIMIT_ENABLE = False
    t1, _ = dos_tenants
    Domain.objects.create(
        domain="aisl-uno.proveedores.localhost",
        tenant=t1,
        is_primary=False,
        es_panel_proveedores=True,
    )
    try:
        # Correo SIN cuenta de proveedor activa: se dice en el paso 1 (registrado=False, decisión
        # de producto) y NO se envía ningún correo ni se muestra pantalla de código.
        r = EspaciosProveedorView().post(_req({"email": "nadie@x.com"}))
        assert r.status_code == 200 and r.data["verificado"] is False
        assert r.data["registrado"] is False
        assert len(mailoutbox) == 0

        # Correo registrado: registrado=True (sin espacios aún) y llega el código de 6 dígitos.
        email = _email_unico("hub")
        with schema_context(t1.schema_name):
            _cuenta(email)
        r = EspaciosProveedorView().post(_req({"email": email}))
        assert r.status_code == 200 and r.data["verificado"] is False
        assert r.data["registrado"] is True
        assert "espacios" not in r.data  # la membresía por-tenant exige probar el correo
        assert len(mailoutbox) == 1
        codigo = re.search(r"\b(\d{6})\b", mailoutbox[0].body).group(1)

        # Código equivocado → 400 genérico.
        mal = VerificarEspaciosView().post(_req({"email": email, "codigo": "000000"}))
        assert mal.status_code == 400

        # Código correcto → espacios (con URL del panel del tenant) + cookie de dispositivo.
        ok = VerificarEspaciosView().post(_req({"email": email, "codigo": codigo}))
        assert ok.status_code == 200 and ok.data["verificado"] is True
        assert [e["nombre"] for e in ok.data["espacios"]] == ["Tenant Uno"]
        assert ok.data["espacios"][0]["url"] == "http://aisl-uno.proveedores.localhost"
        cookie = ok.cookies[COOKIE_DISPOSITIVO].value
        assert cookie

        # El código es de un solo uso.
        repetido = VerificarEspaciosView().post(_req({"email": email, "codigo": codigo}))
        assert repetido.status_code == 400

        # Con la cookie, el paso 1 devuelve los espacios directo (sin nuevo código).
        directo = EspaciosProveedorView().post(
            _req({"email": email}, cookies={COOKIE_DISPOSITIVO: cookie})
        )
        assert directo.status_code == 200 and directo.data["verificado"] is True
        assert len(directo.data["espacios"]) == 1
        assert len(mailoutbox) == 1  # no se envió otro código

        # La cookie de un correo NO sirve para espiar los espacios de otro correo registrado.
        email2 = _email_unico("otro")
        with schema_context(t1.schema_name):
            _cuenta(email2)
        ajeno = EspaciosProveedorView().post(
            _req({"email": email2}, cookies={COOKIE_DISPOSITIVO: cookie})
        )
        assert ajeno.data["verificado"] is False and "espacios" not in ajeno.data
    finally:
        Domain.objects.filter(tenant=t1, es_panel_proveedores=True).delete()


def test_hub_excluye_tenants_cancelados_y_cuentas_inactivas(dos_tenants, settings, mailoutbox):
    from apps.tenants.hub_proveedores_api import EspaciosProveedorView, VerificarEspaciosView
    from apps.tenants.models import Domain, Tenant

    settings.RATELIMIT_ENABLE = False
    t1, t2 = dos_tenants
    for t, dom in ((t1, "aisl-uno.proveedores.localhost"), (t2, "aisl-dos.proveedores.localhost")):
        Domain.objects.create(domain=dom, tenant=t, is_primary=False, es_panel_proveedores=True)
    try:
        email = _email_unico("multi")
        for t in (t1, t2):
            with schema_context(t.schema_name):
                _cuenta(email)

        t2.estado = Tenant.Estado.CANCELADO
        t2.save(update_fields=["estado"])

        EspaciosProveedorView().post(_req({"email": email}))
        codigo = re.search(r"\b(\d{6})\b", mailoutbox[-1].body).group(1)
        ok = VerificarEspaciosView().post(_req({"email": email, "codigo": codigo}))
        # Solo el tenant vivo aparece; el cancelado no se revela.
        assert [e["nombre"] for e in ok.data["espacios"]] == ["Tenant Uno"]

        # Cuentas dadas de baja lógica (en TODOS los tenants): el hub responde registrado=False
        # y deja de enviar códigos.
        from apps.proveedores.models import CuentaProveedor

        for t in (t1, t2):
            with schema_context(t.schema_name):
                c = CuentaProveedor.objects.get(email=email)
                c.activo = False
                c.save(update_fields=["activo"])
        baja = EspaciosProveedorView().post(_req({"email": email}))
        assert baja.data["registrado"] is False
        assert len(mailoutbox) == 1  # ya no hay entradas activas → no se envía código
    finally:
        Domain.objects.filter(es_panel_proveedores=True, tenant__in=[t1, t2]).delete()
        t2.estado = Tenant.Estado.TRIAL
        t2.save(update_fields=["estado"])
