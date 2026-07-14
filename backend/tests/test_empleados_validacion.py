"""Empleado: correo y teléfono obligatorios + dedup de correo por empresa (Proveedor)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def _ser(data, user, instance=None):
    from apps.empleados.serializers import EmpleadoSerializer

    return EmpleadoSerializer(
        instance=instance,
        data=data,
        context={"request": SimpleNamespace(user=user)},
        partial=instance is not None,
    )


def _empresa(nombre, correo):
    from apps.proveedores.models import CuentaProveedor, Proveedor

    prov = Proveedor.objects.create(nombre=nombre)
    cuenta = CuentaProveedor.objects.create_user(
        email=correo, nombre="Resp", password="x", proveedor=prov
    )
    return cuenta


def test_email_y_telefono_son_obligatorios(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cuenta = _empresa("ACME", "r@acme.com")
        s = _ser({"nombre": "Juan"}, cuenta)
        assert not s.is_valid()
        assert "email" in s.errors
        assert "telefono" in s.errors


def test_dedup_email_en_la_misma_empresa(dos_tenants):
    from apps.empleados.models import Empleado

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cuenta = _empresa("ACME", "r@acme.com")
        Empleado.objects.create(
            proveedor=cuenta, nombre="Juan", email="juan@x.com", telefono="8112223344"
        )
        # Mismo correo (aunque cambie mayúsculas) en la misma empresa → inválido.
        s = _ser({"nombre": "Otro", "email": "JUAN@x.com", "telefono": "8112220000"}, cuenta)
        assert not s.is_valid()
        assert "email" in s.errors


def test_dedup_no_cruza_entre_empresas(dos_tenants):
    from apps.empleados.models import Empleado

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        c1 = _empresa("ACME", "a@1.com")
        c2 = _empresa("BETA", "b@2.com")
        Empleado.objects.create(
            proveedor=c1, nombre="Juan", email="juan@x.com", telefono="8112223344"
        )
        # Mismo correo pero OTRA empresa → válido.
        s = _ser({"nombre": "Juan2", "email": "juan@x.com", "telefono": "8112220000"}, c2)
        assert s.is_valid(), s.errors


def test_alta_valida_con_ambos(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cuenta = _empresa("ACME", "r@acme.com")
        s = _ser({"nombre": "Ana", "email": "ana@x.com", "telefono": "55 1234 5678"}, cuenta)
        assert s.is_valid(), s.errors
        assert s.validated_data["telefono"] == "5512345678"  # normalizado a 10 dígitos
        assert s.validated_data["email"] == "ana@x.com"  # minúsculas
