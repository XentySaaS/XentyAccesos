"""Workspace de verificación: agregación proveedor → empleado con conteos por estado.

Ejercita las vistas de agregación (``verificacion_api``) directamente sobre un grafo mínimo
(Proveedor → CuentaProveedor → Empleado → DocumentoEmpleado), sin pasar por la pila de permisos.
"""

from __future__ import annotations

import pytest
from django_tenants.utils import schema_context
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


def _resp(view_cls, query: str = ""):
    return view_cls().get(Request(_factory.get(f"/x/?{query}")))


def _grafo():
    """Crea (en el schema activo) un proveedor con 2 empleados y documentos, y devuelve el proveedor."""
    from apps.documentos.models import DocumentoEmpleado, GrupoDocumentos, TipoDocumento
    from apps.empleados.models import Empleado
    from apps.proveedores.models import CuentaProveedor, Proveedor

    prov = Proveedor.objects.create(nombre="ACME")
    cuenta = CuentaProveedor.objects.create_user(
        email="resp@acme.com", nombre="Resp", password="x", proveedor=prov
    )
    e1 = Empleado.objects.create(nombre="Juan", proveedor=cuenta)
    e2 = Empleado.objects.create(nombre="Ana", proveedor=cuenta)
    g = GrupoDocumentos.objects.create(nombre="G")
    td = TipoDocumento.objects.create(nombre="INE", grupo=g)
    # 2 pendientes (uno por empleado) + 1 aprobado (de Juan)
    DocumentoEmpleado.objects.create(empleado=e1, tipo_documento=td, estado=0)
    DocumentoEmpleado.objects.create(empleado=e2, tipo_documento=td, estado=0)
    DocumentoEmpleado.objects.create(empleado=e1, tipo_documento=td, estado=1)
    return prov


def test_proveedores_agrega_conteos_por_estado(dos_tenants):
    from apps.documentos.verificacion_api import ProveedoresVerificacionView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        prov = _grafo()

        # Pendientes: 2 docs, 2 empleados
        r = _resp(ProveedoresVerificacionView, "estado=0")
        assert r.status_code == 200
        assert len(r.data["results"]) == 1
        row = r.data["results"][0]
        assert row["proveedor_id"] == prov.id
        assert row["proveedor_nombre"] == "ACME"
        assert row["docs"] == 2
        assert row["empleados"] == 2

        # Aprobados: 1 doc, 1 empleado
        r2 = _resp(ProveedoresVerificacionView, "estado=1")
        assert r2.data["results"][0]["docs"] == 1
        assert r2.data["results"][0]["empleados"] == 1

        # Búsqueda por nombre de proveedor
        assert len(_resp(ProveedoresVerificacionView, "estado=0&search=acme").data["results"]) == 1
        assert len(_resp(ProveedoresVerificacionView, "estado=0&search=zzz").data["results"]) == 0


def test_empleados_del_proveedor(dos_tenants):
    from apps.documentos.verificacion_api import EmpleadosVerificacionView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        prov = _grafo()

        r = _resp(EmpleadosVerificacionView, f"estado=0&proveedor={prov.id}")
        assert r.status_code == 200
        filas = r.data["results"]
        assert {f["emp_nombre"] for f in filas} == {"Juan", "Ana"}
        assert all(f["docs"] == 1 for f in filas)

        # Búsqueda por nombre de empleado
        r2 = _resp(EmpleadosVerificacionView, f"estado=0&proveedor={prov.id}&search=jua")
        assert [f["emp_nombre"] for f in r2.data["results"]] == ["Juan"]


def test_proveedores_orden(dos_tenants):
    """`orden=az` alfabético; default (pendientes) por más documentos primero."""
    from apps.documentos.models import DocumentoEmpleado, GrupoDocumentos, TipoDocumento
    from apps.documentos.verificacion_api import ProveedoresVerificacionView
    from apps.empleados.models import Empleado
    from apps.proveedores.models import CuentaProveedor, Proveedor

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        g = GrupoDocumentos.objects.create(nombre="G")
        td = TipoDocumento.objects.create(nombre="INE", grupo=g)
        # Zeta: 1 doc; Alfa: 2 docs.
        pz = Proveedor.objects.create(nombre="Zeta")
        cz = CuentaProveedor.objects.create_user(
            email="z@z.com", nombre="Z", password="x", proveedor=pz
        )
        DocumentoEmpleado.objects.create(
            empleado=Empleado.objects.create(nombre="e", proveedor=cz), tipo_documento=td, estado=0
        )
        pa = Proveedor.objects.create(nombre="Alfa")
        ca = CuentaProveedor.objects.create_user(
            email="a@a.com", nombre="A", password="x", proveedor=pa
        )
        for _i in range(2):
            DocumentoEmpleado.objects.create(
                empleado=Empleado.objects.create(nombre="e", proveedor=ca),
                tipo_documento=td,
                estado=0,
            )

        # Default (pendientes): Alfa (2 docs) antes que Zeta (1 doc).
        r = _resp(ProveedoresVerificacionView, "estado=0")
        assert [x["proveedor_nombre"] for x in r.data["results"]] == ["Alfa", "Zeta"]
        # A-Z: alfabético.
        r2 = _resp(ProveedoresVerificacionView, "estado=0&orden=az")
        assert [x["proveedor_nombre"] for x in r2.data["results"]] == ["Alfa", "Zeta"]
        # Z-A: inverso.
        r3 = _resp(ProveedoresVerificacionView, "estado=0&orden=za")
        assert [x["proveedor_nombre"] for x in r3.data["results"]] == ["Zeta", "Alfa"]


def test_empleados_sin_proveedor_es_400(dos_tenants):
    from apps.documentos.verificacion_api import EmpleadosVerificacionView

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        _grafo()
        assert _resp(EmpleadosVerificacionView, "estado=0").status_code == 400
