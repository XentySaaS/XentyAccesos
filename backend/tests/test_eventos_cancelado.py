"""Eventos: un evento cancelado es terminal — no se edita ni admite nuevas invitaciones."""

from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def _evento(estado=None):
    from apps.accounts.models import Usuario
    from apps.eventos.models import Evento
    from apps.recintos.models import Recinto

    u = Usuario.objects.create_user(
        email="ev@x.com", nombre="Org", password="x", rol=Usuario.Rol.ADMINISTRADOR
    )
    rec = Recinto.objects.create(nombre="Recinto Ev")
    ev = Evento.objects.create(
        nombre="Evento Test",
        creado_por=u,
        recinto=rec,
        vigencia_inicio=datetime.date(2026, 7, 1),
        vigencia_fin=datetime.date(2026, 7, 2),
        estado=estado or Evento.Estado.CANCELADO,
    )
    return ev, u


def test_no_editar_evento_cancelado(dos_tenants):
    from rest_framework.exceptions import PermissionDenied

    from apps.eventos.serializers import EventoSerializer
    from apps.eventos.views import EventoViewSet

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        ev, u = _evento()
        vs = EventoViewSet()
        vs.request = SimpleNamespace(user=u)
        with pytest.raises(PermissionDenied):
            vs.perform_update(EventoSerializer(instance=ev))
