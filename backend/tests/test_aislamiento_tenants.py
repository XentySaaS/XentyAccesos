"""Suite de aislamiento entre tenants — OBLIGATORIA (CLAUDE.md §4).

Ejecutar solo esta suite:  ``pytest -k aislamiento``

Verifica la garantía central del multitenancy de Xenty Acceso: *el aislamiento es por base de
datos, no por disciplina de código*. En concreto:

- Los datos de un tenant (``Usuario``, ``Proveedor``, resultados 69-B) NUNCA son visibles desde
  otro tenant (viven en schemas PostgreSQL distintos).
- El padrón EFOS 69-B es GLOBAL (``apps.efos`` en ``SHARED_APPS``, schema ``public``): SÍ es
  visible desde cualquier tenant, pero los RESULTADOS de validación son por tenant.
- La cache (Redis) y el storage de archivos quedan segregados por schema.

Requiere PostgreSQL real (django-tenants). Cada prueba crea/lee datos dentro de un
``schema_context`` y confía en la reversión transaccional de ``django_db`` para no dejar residuos.
"""

import pytest
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import connection
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


# ── Aislamiento de datos operativos (data plane) ─────────────────────────────


def test_aislamiento_usuarios_no_filtran_entre_tenants(dos_tenants):
    """Un ``Usuario`` creado en el schema de un tenant no existe en el otro."""
    from apps.accounts.models import Usuario

    t1, t2 = dos_tenants

    with schema_context(t1.schema_name):
        Usuario.objects.create_user(email="solo-t1@x.mx", nombre="Uno", password="Secreta123!")
        assert Usuario.objects.filter(email="solo-t1@x.mx").exists()

    with schema_context(t2.schema_name):
        assert not Usuario.objects.filter(
            email="solo-t1@x.mx"
        ).exists(), "Fuga: el usuario del tenant 1 es visible desde el tenant 2"
        Usuario.objects.create_user(email="solo-t2@x.mx", nombre="Dos", password="Secreta123!")

    with schema_context(t1.schema_name):
        assert not Usuario.objects.filter(
            email="solo-t2@x.mx"
        ).exists(), "Fuga: el usuario del tenant 2 es visible desde el tenant 1"


def test_aislamiento_proveedores_no_filtran_entre_tenants(dos_tenants):
    """Un ``Proveedor`` del tenant 1 no aparece en el conteo del tenant 2."""
    from apps.proveedores.models import Proveedor

    t1, t2 = dos_tenants

    with schema_context(t1.schema_name):
        Proveedor.objects.create(nombre="ACME T1", rfc="AAA010101AA1")
        assert Proveedor.objects.count() == 1

    with schema_context(t2.schema_name):
        assert (
            Proveedor.objects.count() == 0
        ), "Fuga: proveedores del tenant 1 visibles desde el tenant 2"


def test_aislamiento_preferencia_mensajeria_por_tenant(dos_tenants):
    """La ``PreferenciaMensajeria`` (F-B) vive en el schema del tenant → no filtra entre tenants."""
    from apps.mensajeria.models import PreferenciaMensajeria

    t1, t2 = dos_tenants

    with schema_context(t1.schema_name):
        pref = PreferenciaMensajeria.cargar()
        pref.proveedores_orden = ["ultramsg", "xcc"]
        pref.failover_habilitado = False
        pref.save()

    with schema_context(t2.schema_name):
        # El tenant 2 arranca con su propio singleton por defecto, no el del tenant 1.
        pref2 = PreferenciaMensajeria.cargar()
        assert pref2.proveedores_orden == []
        assert pref2.failover_habilitado is True, "Fuga: la preferencia del tenant 1 se ve en el 2"

    with schema_context(t1.schema_name):
        pref1 = PreferenciaMensajeria.cargar()
        assert pref1.proveedores_orden == ["ultramsg", "xcc"]


# ── Padrón EFOS 69-B: global visible; resultados por tenant ──────────────────


def test_aislamiento_padron_efos_es_global_para_todos_los_tenants(dos_tenants):
    """``SatEfo`` vive en ``public`` (SHARED_APPS) → visible desde cualquier tenant."""
    from apps.efos.models import SatEfo

    t1, t2 = dos_tenants

    # Se escribe en contexto público (fuera de schema_context): tabla en el schema ``public``.
    SatEfo.objects.create(rfc="EFO010101AAA", nombre="EFO Global", situacion="Definitivo")

    for t in (t1, t2):
        with schema_context(t.schema_name):
            assert SatEfo.objects.filter(
                rfc="EFO010101AAA"
            ).exists(), f"El padrón EFOS global debe ser visible desde el tenant {t.schema_name}"


def test_aislamiento_resultados_69b_son_por_tenant(dos_tenants):
    """Los ``ResultadoLista69b`` (validación) SÍ son por tenant, aunque el padrón sea global."""
    from apps.cumplimiento.models import ConsultaLista69b, ResultadoLista69b
    from apps.proveedores.models import Proveedor

    t1, t2 = dos_tenants

    with schema_context(t1.schema_name):
        prov = Proveedor.objects.create(nombre="Prov T1", rfc="AAA010101AA1")
        consulta = ConsultaLista69b.objects.create()
        ResultadoLista69b.objects.create(
            consulta=consulta,
            proveedor=prov,
            rfc="AAA010101AA1",
            estado=ResultadoLista69b.Estado.ENCONTRADO,
        )
        assert ResultadoLista69b.objects.count() == 1

    with schema_context(t2.schema_name):
        assert (
            ResultadoLista69b.objects.count() == 0
        ), "Fuga: los resultados de validación 69-B del tenant 1 se ven desde el tenant 2"


# ── Aislamiento de cache (Redis) por schema ──────────────────────────────────


def test_aislamiento_cache_por_tenant(dos_tenants):
    """La misma clave de cache guarda valores independientes por tenant (``tenant_key_func``)."""
    t1, t2 = dos_tenants
    clave = "aislamiento_probe"
    try:
        with schema_context(t1.schema_name):
            cache.set(clave, "valor-t1", 30)
        with schema_context(t2.schema_name):
            assert cache.get(clave) is None, "Fuga: la cache del tenant 1 se lee desde el tenant 2"
            cache.set(clave, "valor-t2", 30)
        with schema_context(t1.schema_name):
            assert cache.get(clave) == "valor-t1"
        with schema_context(t2.schema_name):
            assert cache.get(clave) == "valor-t2"
    finally:
        # Redis no participa de la reversión transaccional: limpiar a mano.
        for t in (t1, t2):
            with schema_context(t.schema_name):
                cache.delete(clave)


def test_aislamiento_cache_key_func_prefija_el_schema(dos_tenants):
    """La función de clave prefija con el schema activo → claves distintas por tenant."""
    from common.cache import tenant_key_func

    t1, t2 = dos_tenants
    with schema_context(t1.schema_name):
        k1 = tenant_key_func("x", "pref", 1)
    with schema_context(t2.schema_name):
        k2 = tenant_key_func("x", "pref", 1)

    assert k1 != k2
    assert t1.schema_name in k1 and t2.schema_name in k2


# ── Aislamiento de storage de archivos por schema ────────────────────────────


def test_aislamiento_storage_por_tenant(dos_tenants):
    """El storage (``TenantFileSystemStorage``) resuelve rutas distintas por schema."""
    t1, t2 = dos_tenants
    with schema_context(t1.schema_name):
        p1 = default_storage.path("empleados/foto.png")
    with schema_context(t2.schema_name):
        p2 = default_storage.path("empleados/foto.png")

    assert p1 != p2, "Fuga: dos tenants comparten la misma ruta de archivo"
    assert t1.schema_name in p1 and t2.schema_name in p2


# ── El data plane no contamina el schema público ─────────────────────────────


def test_aislamiento_tablas_de_tenant_no_existen_en_public(dos_tenants):
    """Las tablas de ``TENANT_APPS`` solo existen en el schema del tenant, nunca en ``public``.

    Garantía estructural: ``accounts_usuario`` es una app de tenant, así que su tabla se crea en
    cada schema de tenant pero NO en ``public``. La ausencia física de la tabla en el schema
    público es una barrera más fuerte que un simple filtro por columna.
    """
    t1, _ = dos_tenants

    # Fuera de cualquier schema_context la conexión de test apunta al schema público.
    assert connection.schema_name == "public"

    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'accounts_usuario'"
        )
        assert (
            cur.fetchone() is None
        ), "Fuga estructural: la tabla accounts_usuario existe en el schema público"
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = 'accounts_usuario'",
            [t1.schema_name],
        )
        assert (
            cur.fetchone() is not None
        ), "La tabla accounts_usuario debe existir en el schema del tenant"
