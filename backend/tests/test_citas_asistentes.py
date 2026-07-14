"""Citas — alta/baja de asistentes (baja lógica).

Verifica que dar de baja un asistente es **baja lógica** (estado=CANCELADO, no borrado físico; el
escáner ya lo bloquea), que `_guardar_asistentes` devuelve los creados (para invitar solo a los
nuevos), y que una cita con todos sus asistentes dados de baja se puede borrar (guard).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def _cita_directa():
    """Crea (en el schema activo) una cita Directa mínima y devuelve (cita, usuario)."""
    from apps.accounts.models import Usuario
    from apps.citas.models import Cita
    from apps.recintos.models import Recinto

    u = Usuario.objects.create_user(
        email="op@x.com", nombre="Op", password="x", rol=Usuario.Rol.ADMINISTRADOR
    )
    rec = Recinto.objects.create(nombre="Recinto Test")
    cita = Cita.objects.create(
        nombre="Cita Test", tipo=Cita.Tipo.DIRECTA, recinto=rec, creado_por_usuario=u
    )
    return cita, u


def test_asistente_baja_es_logica(dos_tenants, monkeypatch):
    """DELETE del asistente = estado CANCELADO, no borrado físico."""
    monkeypatch.setattr("apps.citas.services.enviar_baja_asistente", lambda *a, **k: True)
    from apps.citas.models import AsistenteCita
    from apps.citas.views import AsistenteCitaViewSet

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cita, u = _cita_directa()
        asis = AsistenteCita.objects.create(cita=cita, nombre="Juan")

        vs = AsistenteCitaViewSet()
        vs.request = SimpleNamespace(user=u)
        vs.perform_destroy(asis)

        asis.refresh_from_db()
        assert asis.estado == AsistenteCita.Estado.CANCELADO
        assert AsistenteCita.objects.filter(pk=asis.pk).exists()  # no se borró físicamente


def test_guardar_asistentes_devuelve_creados(dos_tenants):
    from apps.citas.models import AsistenteCita
    from apps.citas.serializers import CitaSerializer

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cita, _u = _cita_directa()
        creados = CitaSerializer._guardar_asistentes(
            cita, [{"nombre": "Ana", "email": "ana@x.com", "telefono": "8112223344"}]
        )
        assert len(creados) == 1
        assert isinstance(creados[0], AsistenteCita)
        assert cita.asistentes.count() == 1
        # El teléfono se normalizó a 10 dígitos (TelefonoField en el input serializer no aplica aquí,
        # pero _guardar_asistentes guarda tal cual lo recibe): queda registrado.
        assert creados[0].nombre == "Ana"


def test_cita_borrable_si_todos_los_asistentes_dados_de_baja(dos_tenants):
    """Una cita Directa cuyos asistentes están todos CANCELADOS sí se puede borrar (guard)."""
    from apps.citas.models import AsistenteCita, Cita
    from apps.citas.views import CitaViewSet

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cita, u = _cita_directa()
        AsistenteCita.objects.create(
            cita=cita, nombre="Juan", estado=AsistenteCita.Estado.CANCELADO
        )

        vs = CitaViewSet()
        vs.request = SimpleNamespace(user=u)
        vs.perform_destroy(cita)  # no debe lanzar PermissionDenied

        assert not Cita.objects.filter(pk=cita.pk).exists()


def test_cita_no_borrable_con_asistente_activo(dos_tenants):
    from rest_framework.exceptions import PermissionDenied

    from apps.citas.models import AsistenteCita, Cita
    from apps.citas.views import CitaViewSet

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cita, u = _cita_directa()
        AsistenteCita.objects.create(cita=cita, nombre="Juan")  # activo (PENDIENTE)

        vs = CitaViewSet()
        vs.request = SimpleNamespace(user=u)
        with pytest.raises(PermissionDenied):
            vs.perform_destroy(cita)
        assert Cita.objects.filter(pk=cita.pk).exists()
