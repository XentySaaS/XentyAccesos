"""Endpoint de configuración de retención (UI de Catálogos): GET efectivo + PUT con validación.

Ejercita ``RetencionAuditoriaView`` directamente en un tenant (sin la pila de permisos), como en
``test_verificacion_workspace``.
"""

from __future__ import annotations

import pytest
from django_tenants.utils import schema_context
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


def _put(data: dict) -> Request:
    """DRF Request con parser JSON (un Request "pelón" no trae parsers y no parsea el body)."""
    return Request(_factory.put("/x/", data, format="json"), parsers=[JSONParser()])


def test_get_devuelve_default_cuando_no_hay_opcion(dos_tenants, settings):
    from apps.config.views import RetencionAuditoriaView

    settings.RETENCION_HISTORIAL_DIAS = 365
    settings.RETENCION_BITACORA_DIAS = 200
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r = RetencionAuditoriaView().get(Request(_factory.get("/x/")))
    assert r.data["historial"] == {"dias": 365, "personalizado": False, "default": 365}
    assert r.data["bitacora"] == {"dias": 200, "personalizado": False, "default": 200}


def test_put_guarda_opcion_y_get_lo_refleja(dos_tenants, settings):
    from apps.config.models import Opcion
    from apps.config.views import RetencionAuditoriaView

    settings.RETENCION_HISTORIAL_DIAS = 365
    settings.RETENCION_BITACORA_DIAS = 365
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r = RetencionAuditoriaView().put(_put({"historial_dias": 90, "bitacora_dias": 30}))
        assert r.data["historial"]["dias"] == 90
        assert r.data["historial"]["personalizado"] is True
        assert r.data["bitacora"]["dias"] == 30
        assert Opcion.objects.get(clave="retencion_historial_dias").valor == "90"
        assert Opcion.objects.get(clave="retencion_bitacora_dias").valor == "30"


def test_put_cero_es_valido(dos_tenants):
    from apps.config.views import RetencionAuditoriaView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r = RetencionAuditoriaView().put(_put({"historial_dias": 0}))
    assert r.data["historial"]["dias"] == 0  # 0 = conservar siempre


def test_put_rechaza_valores_invalidos(dos_tenants):
    from apps.config.views import RetencionAuditoriaView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r_neg = RetencionAuditoriaView().put(_put({"historial_dias": -5}))
        r_txt = RetencionAuditoriaView().put(_put({"bitacora_dias": "abc"}))
        r_alto = RetencionAuditoriaView().put(_put({"historial_dias": 99999}))
    assert r_neg.status_code == 400 and "historial_dias" in r_neg.data
    assert r_txt.status_code == 400 and "bitacora_dias" in r_txt.data
    assert r_alto.status_code == 400 and "historial_dias" in r_alto.data
