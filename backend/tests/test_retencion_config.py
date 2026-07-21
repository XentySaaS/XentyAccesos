"""Endpoint de configuración de retención (pantalla Configuración): GET efectivo + PUT con validación.

Retención en MESES, obligatoria 1–5 (por suscripción). Ejercita ``RetencionAuditoriaView``
directamente en un tenant (sin la pila de permisos), como en ``test_verificacion_workspace``.
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


def test_get_devuelve_default_y_rango(dos_tenants, settings):
    from apps.config.views import RetencionAuditoriaView

    settings.RETENCION_HISTORIAL_MESES = 3
    settings.RETENCION_BITACORA_MESES = 5
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r = RetencionAuditoriaView().get(Request(_factory.get("/x/")))
    assert r.data["historial"] == {"meses": 3, "personalizado": False, "default": 3}
    assert r.data["bitacora"] == {"meses": 5, "personalizado": False, "default": 5}
    assert r.data["min"] == 1 and r.data["max"] == 5


def test_put_guarda_opcion_y_get_lo_refleja(dos_tenants, settings):
    from apps.config.models import Opcion
    from apps.config.views import RetencionAuditoriaView

    settings.RETENCION_HISTORIAL_MESES = 3
    settings.RETENCION_BITACORA_MESES = 3
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r = RetencionAuditoriaView().put(_put({"historial_meses": 2, "bitacora_meses": 1}))
        assert r.data["historial"]["meses"] == 2
        assert r.data["historial"]["personalizado"] is True
        assert r.data["bitacora"]["meses"] == 1
        assert Opcion.objects.get(clave="retencion_historial_meses").valor == "2"
        assert Opcion.objects.get(clave="retencion_bitacora_meses").valor == "1"


def test_put_rechaza_fuera_de_rango_y_no_entero(dos_tenants):
    from apps.config.views import RetencionAuditoriaView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r_cero = RetencionAuditoriaView().put(_put({"historial_meses": 0}))  # obligatorio ≥ 1
        r_alto = RetencionAuditoriaView().put(_put({"bitacora_meses": 6}))  # > 5
        r_txt = RetencionAuditoriaView().put(_put({"historial_meses": "abc"}))
    assert r_cero.status_code == 400 and "historial_meses" in r_cero.data
    assert r_alto.status_code == 400 and "bitacora_meses" in r_alto.data
    assert r_txt.status_code == 400 and "historial_meses" in r_txt.data


def test_put_acepta_limites(dos_tenants):
    from apps.config.views import RetencionAuditoriaView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        r = RetencionAuditoriaView().put(_put({"historial_meses": 1, "bitacora_meses": 5}))
    assert r.data["historial"]["meses"] == 1
    assert r.data["bitacora"]["meses"] == 5
