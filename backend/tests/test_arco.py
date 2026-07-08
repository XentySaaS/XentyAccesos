"""ARCO / LFPDPPP: export (acceso) y cancelación (anonimización) de titulares del tenant.

Cubre que el export descifra PII, que la cancelación anonimiza + marca baja + preserva la fila, que
es idempotente, y que las solicitudes/aviso viven por tenant (aislamiento).
"""

import pytest
from django_tenants.utils import schema_context

from apps.cumplimiento import arco
from apps.cumplimiento.arco import PLACEHOLDER
from apps.cumplimiento.models import TitularTipo

pytestmark = pytest.mark.django_db


def _cuenta(email="rep@empresa.mx", **kw):
    from apps.proveedores.models import CuentaProveedor

    cuenta = CuentaProveedor(nombre="Juan Pérez", email=email, **kw)
    cuenta.set_password("Secreta123!")
    cuenta.save()
    return cuenta


def _empleado(cuenta, **kw):
    from apps.empleados.models import Empleado

    return Empleado.objects.create(proveedor=cuenta, nombre="Pedro López", **kw)


def test_export_empleado_incluye_pii(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        emp = _empleado(_cuenta(), email="pedro@e.mx", telefono="8112223344")
        data = arco.exportar_titular(TitularTipo.EMPLEADO, emp.id)
    dp = data["datos_personales"]
    assert dp["nombre"] == "Pedro López" and dp["email"] == "pedro@e.mx"
    assert dp["telefono"] == "8112223344"


def test_export_cuenta_descifra_curp_y_nss(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cta = _cuenta(email="titular@e.mx", curp="PELP900101HDFRRD09", nss="12345678901")
        data = arco.exportar_titular(TitularTipo.CUENTA_PROVEEDOR, cta.id)
    dp = data["datos_personales"]
    assert dp["curp"] == "PELP900101HDFRRD09"  # descifrado por el field
    assert dp["nss"] == "12345678901"


def test_cancelar_empleado_anonimiza_y_preserva_fila(dos_tenants):
    from apps.empleados.models import Empleado

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        emp = _empleado(_cuenta(), email="pedro@e.mx", telefono="8112223344")
        arco.cancelar_titular(TitularTipo.EMPLEADO, emp.id)
        emp.refresh_from_db()
        assert emp.nombre == PLACEHOLDER
        assert emp.email is None and emp.telefono is None
        assert emp.estado == Empleado.Estado.BAJA
        # La fila se conserva (baja lógica + integridad referencial), no se borra.
        assert Empleado.objects.filter(id=emp.id).exists()


def test_cancelar_cuenta_anonimiza_pii_sensible(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        cta = _cuenta(email="titular@e.mx", curp="PELP900101HDFRRD09", nss="12345678901")
        arco.cancelar_titular(TitularTipo.CUENTA_PROVEEDOR, cta.id)
        cta.refresh_from_db()
        assert cta.nombre == PLACEHOLDER
        assert cta.curp is None and cta.nss is None
        assert cta.activo is False
        assert cta.email == f"cancelado-{cta.pk}@anonimizado.local"
        assert not cta.has_usable_password()


def test_cancelar_es_idempotente(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        emp = _empleado(_cuenta(email="rep2@e.mx"))
        arco.cancelar_titular(TitularTipo.EMPLEADO, emp.id)
        # Segunda pasada no debe lanzar ni cambiar el resultado.
        res = arco.cancelar_titular(TitularTipo.EMPLEADO, emp.id)
        assert res["estado"] == "anonimizado"


def test_exportar_inexistente_devuelve_none(dos_tenants):
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        assert arco.exportar_titular(TitularTipo.ASISTENTE, 999999) is None


def test_aislamiento_solicitudes_y_documentos_por_tenant(dos_tenants):
    """SolicitudArco y DocumentoLegal viven en el schema del tenant → no filtran entre tenants."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.cumplimiento.models import DocumentoLegal, SolicitudArco

    t1, t2 = dos_tenants
    with schema_context(t1.schema_name):
        SolicitudArco.objects.create(
            tipo=SolicitudArco.Tipo.ACCESO,
            titular_tipo=TitularTipo.EMPLEADO,
            titular_id=1,
            titular_desc="P***",
            plazo_limite=timezone.now().date() + timedelta(days=20),
        )
        DocumentoLegal.objects.create(
            tipo=DocumentoLegal.Tipo.AVISO_PRIVACIDAD, texto="Aviso T1", version=1
        )

    with schema_context(t2.schema_name):
        assert SolicitudArco.objects.count() == 0, "Fuga: solicitud ARCO del tenant 1 vista en el 2"
        assert DocumentoLegal.objects.count() == 0, "Fuga: documento del tenant 1 visto en el 2"


def test_documento_versionado_e_independiente_por_tipo(dos_tenants):
    from apps.cumplimiento.arco_api import documento_vigente
    from apps.cumplimiento.models import DocumentoLegal

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        DocumentoLegal.objects.create(
            tipo=DocumentoLegal.Tipo.AVISO_PRIVACIDAD, texto="aviso v1", version=1
        )
        DocumentoLegal.objects.create(
            tipo=DocumentoLegal.Tipo.AVISO_PRIVACIDAD, texto="aviso v2", version=2
        )
        DocumentoLegal.objects.create(
            tipo=DocumentoLegal.Tipo.TERMINOS, texto="terminos v1", version=1
        )
        # El vigente es la versión más alta de CADA tipo, independientes entre sí.
        assert documento_vigente(DocumentoLegal.Tipo.AVISO_PRIVACIDAD).texto == "aviso v2"
        assert documento_vigente(DocumentoLegal.Tipo.TERMINOS).texto == "terminos v1"
