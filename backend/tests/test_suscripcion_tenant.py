"""Suscripción autoservicio del tenant: GET resumen + POST cancelar (zona peligrosa).

Ejercita ``SuscripcionTenantView`` directamente dentro del schema del tenant (sin la pila de
permisos). El fixture ``dos_tenants`` es module-scoped, así que cada test fija el ``estado`` que
necesita para ser independiente del orden.
"""

from __future__ import annotations

import pytest
from django_tenants.utils import schema_context
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


def _post(data: dict) -> Request:
    return Request(_factory.post("/x/", data, format="json"), parsers=[JSONParser()])


def _fijar_estado(schema_name: str, estado: str) -> None:
    from apps.tenants.models import Tenant

    Tenant.objects.filter(schema_name=schema_name).update(estado=estado)


def test_get_devuelve_resumen(dos_tenants):
    from apps.tenants.models import Tenant
    from apps.tenants.suscripcion_api import SuscripcionTenantView

    t1, _ = dos_tenants
    _fijar_estado(t1.schema_name, Tenant.Estado.TRIAL)
    with schema_context(t1.schema_name):
        r = SuscripcionTenantView().get(Request(_factory.get("/x/")))
    assert r.status_code == 200
    assert r.data["tenant"]["nombre"] == "Tenant Uno"
    assert r.data["tenant"]["estado_label"]  # etiqueta legible presente
    assert r.data["plan"] is None  # el fixture no asigna plan


def test_cancel_confirmacion_incorrecta_no_cancela(dos_tenants):
    from apps.tenants.models import Tenant
    from apps.tenants.suscripcion_api import SuscripcionTenantView

    t1, _ = dos_tenants
    _fijar_estado(t1.schema_name, Tenant.Estado.ACTIVO)
    with schema_context(t1.schema_name):
        r = SuscripcionTenantView().post(_post({"confirmacion": "otra cosa"}))
    assert r.status_code == 400
    assert Tenant.objects.get(schema_name=t1.schema_name).estado == Tenant.Estado.ACTIVO


def test_cancel_confirmacion_correcta_cancela(dos_tenants):
    from apps.tenants.models import Tenant
    from apps.tenants.suscripcion_api import SuscripcionTenantView

    t1, _ = dos_tenants
    _fijar_estado(t1.schema_name, Tenant.Estado.ACTIVO)
    with schema_context(t1.schema_name):
        # Confirmación tolerante a mayúsculas/espacios.
        r = SuscripcionTenantView().post(_post({"confirmacion": "  tenant uno "}))
    assert r.status_code == 200
    assert r.data["tenant"]["estado"] == Tenant.Estado.CANCELADO
    assert Tenant.objects.get(schema_name=t1.schema_name).estado == Tenant.Estado.CANCELADO


def test_cancel_ya_cancelado_es_409(dos_tenants):
    from apps.tenants.models import Tenant
    from apps.tenants.suscripcion_api import SuscripcionTenantView

    t1, _ = dos_tenants
    _fijar_estado(t1.schema_name, Tenant.Estado.CANCELADO)
    with schema_context(t1.schema_name):
        r = SuscripcionTenantView().post(_post({"confirmacion": "Tenant Uno"}))
    assert r.status_code == 409
