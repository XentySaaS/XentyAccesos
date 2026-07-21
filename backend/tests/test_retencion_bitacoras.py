"""Purga de auditoría por retención (Celery): historial de cambios + accesos al sistema.

Ejercita ``purgar_tenant`` sobre un grafo mínimo, con ``creado`` forzado (``update`` salta el
``auto_now_add``). Cubre: borra antiguos / conserva recientes, override por tenant vía ``Opcion``,
``0`` = conservar siempre, aislamiento entre tenants y ``dry_run``.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def _historial(dias: int) -> None:
    """Crea un HistorialCambio con ``creado`` hace ``dias`` días (en el schema activo)."""
    from apps.config.models import HistorialCambio

    h = HistorialCambio.objects.create(descripcion="cambio")
    HistorialCambio.objects.filter(pk=h.pk).update(creado=timezone.now() - timedelta(days=dias))


def _bitacora(dias: int) -> None:
    from apps.config.models import BitacoraAcceso

    b = BitacoraAcceso.objects.create(
        evento=BitacoraAcceso.Evento.LOGIN,
        contexto=BitacoraAcceso.Contexto.ACCESO,
        actor_email="a@a.com",
    )
    BitacoraAcceso.objects.filter(pk=b.pk).update(creado=timezone.now() - timedelta(days=dias))


def test_borra_antiguos_conserva_recientes(dos_tenants, settings):
    from apps.config.models import BitacoraAcceso, HistorialCambio
    from apps.config.tasks import purgar_tenant

    settings.RETENCION_HISTORIAL_DIAS = 365
    settings.RETENCION_BITACORA_DIAS = 365
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        _historial(400)  # antiguo → se borra
        _historial(10)  # reciente → se conserva
        _bitacora(400)
        _bitacora(10)

    r = purgar_tenant(t1.schema_name)
    assert r["historial"] == 1
    assert r["bitacora"] == 1
    with schema_context(t1.schema_name):
        assert HistorialCambio.objects.count() == 1
        assert BitacoraAcceso.objects.count() == 1


def test_retencion_cero_conserva_todo(dos_tenants, settings):
    from apps.config.models import HistorialCambio, Opcion
    from apps.config.tasks import RETENCION_HISTORIAL_CLAVE, purgar_tenant

    settings.RETENCION_HISTORIAL_DIAS = 365
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        Opcion.objects.create(clave=RETENCION_HISTORIAL_CLAVE, valor="0")  # desactiva la purga
        _historial(1000)

    r = purgar_tenant(t1.schema_name)
    assert r["historial"] == 0
    with schema_context(t1.schema_name):
        assert HistorialCambio.objects.count() == 1


def test_override_opcion_por_tenant(dos_tenants, settings):
    from apps.config.models import BitacoraAcceso, Opcion
    from apps.config.tasks import RETENCION_BITACORA_CLAVE, purgar_tenant

    settings.RETENCION_BITACORA_DIAS = 365  # default largo…
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        Opcion.objects.create(
            clave=RETENCION_BITACORA_CLAVE, valor="10"
        )  # …pero el tenant baja a 10
        _bitacora(20)  # 20 días: con 365 se conservaría, con 10 se borra

    r = purgar_tenant(t1.schema_name)
    assert r["bitacora"] == 1
    with schema_context(t1.schema_name):
        assert BitacoraAcceso.objects.count() == 0


def test_aislamiento_entre_tenants(dos_tenants, settings):
    from apps.config.models import HistorialCambio
    from apps.config.tasks import purgar_tenant

    settings.RETENCION_HISTORIAL_DIAS = 365
    t1, t2 = dos_tenants
    for t in (t1, t2):
        with schema_context(t.schema_name):
            _historial(400)

    purgar_tenant(t1.schema_name)  # solo t1
    with schema_context(t1.schema_name):
        assert HistorialCambio.objects.count() == 0
    with schema_context(t2.schema_name):
        assert HistorialCambio.objects.count() == 1  # t2 intacto


def test_dry_run_no_borra(dos_tenants, settings):
    from apps.config.models import HistorialCambio
    from apps.config.tasks import purgar_tenant

    settings.RETENCION_HISTORIAL_DIAS = 365
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        _historial(400)

    r = purgar_tenant(t1.schema_name, dry_run=True)
    assert r["historial"] == 1  # cuenta lo que se borraría…
    with schema_context(t1.schema_name):
        assert HistorialCambio.objects.count() == 1  # …pero no borra
