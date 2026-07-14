"""Buscador del padrón EFOS 69-B (SatEfoViewSet): por RFC, por razón social y filtro de situación.

Ejercita los filter_backends del viewset (DjangoFilterBackend + SearchFilter) directamente sobre el
queryset, sin pasar por la pila de permisos (que se cubre en otros tests). El padrón es global
(``apps.efos`` en SHARED_APPS, schema ``public``): las filas se crean fuera de ``schema_context``.
"""

from __future__ import annotations

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


def _buscar(query: str):
    from apps.cumplimiento.views import SatEfoViewSet

    vs = SatEfoViewSet()
    vs.request = Request(_factory.get(f"/x/?{query}"))
    return [e.rfc for e in vs.filter_queryset(vs.get_queryset())]


def test_busqueda_efos(dos_tenants):
    from apps.efos.models import SatEfo

    SatEfo.objects.create(
        rfc="GONZ800101AAA", nombre="GONZALEZ MARTINEZ ALBA", situacion="Definitivo"
    )
    SatEfo.objects.create(rfc="XAXX010101000", nombre="OTRA EMPRESA SA DE CV", situacion="Presunto")

    # Por razón social (case-insensitive)
    assert _buscar("search=gonzalez") == ["GONZ800101AAA"]
    # Por RFC parcial
    assert _buscar("search=XAXX") == ["XAXX010101000"]
    # Filtro por situación (exacto)
    assert _buscar("situacion=Presunto") == ["XAXX010101000"]
    # Búsqueda que no coincide con nada
    assert _buscar("search=zzzzz") == []
