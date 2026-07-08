"""F-A — Router de mensajería: proveedor tras interfaz, failover, circuit breaker, ledger.

Verifica la maquinaria de resiliencia del seam (ARQUITECTURA_CONNECTOR §6/§9) sin depender del
Connector: se simula un proveedor que falla y se comprueba el failover y la apertura del breaker.
"""

import pytest
from django_tenants.utils import schema_context

from apps.mensajeria import router
from apps.mensajeria.breaker import CircuitBreaker
from apps.mensajeria.proveedores import ResultadoEnvio, SandboxProvider

pytestmark = pytest.mark.django_db


class _ProveedorFalla:
    nombre = "falla"

    def enviar(self, telefono, cuerpo, archivo=None):
        return ResultadoEnvio(ok=False, proveedor=self.nombre, error="boom")


def test_sandbox_provider_ok():
    res = SandboxProvider().enviar("5218112223344", "hola")
    assert res.ok and res.proveedor == "sandbox" and res.external_id


def test_router_envia_y_registra_sin_pii(dos_tenants):
    from apps.mensajeria.models import RegistroEnvio

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        n0 = RegistroEnvio.objects.count()
        res = router.enviar("5218112223344", "hola")
        assert res.ok
        assert RegistroEnvio.objects.count() == n0 + 1
        reg = RegistroEnvio.objects.latest("creado")
        assert reg.destino_mascara == "****3344"  # sólo máscara, no el teléfono completo


def test_failover_al_siguiente_proveedor(dos_tenants, monkeypatch):
    t1, _ = dos_tenants
    monkeypatch.setattr(
        router, "proveedores_para", lambda tenant, **kw: [_ProveedorFalla(), SandboxProvider()]
    )
    with schema_context(t1.schema_name):
        CircuitBreaker("falla").registrar_exito()  # estado limpio
        res = router.enviar("5218112223344", "hola", registrar=False)
    assert res.ok and res.proveedor == "sandbox"


def test_circuit_breaker_abre_tras_umbral(dos_tenants, monkeypatch):
    t1, _ = dos_tenants
    monkeypatch.setattr(router, "proveedores_para", lambda tenant, **kw: [_ProveedorFalla()])
    with schema_context(t1.schema_name):
        CircuitBreaker("falla").registrar_exito()  # reset
        for _ in range(3):  # cada llamada = 2 intentos → 6 fallos ≥ umbral(5)
            router.enviar("5218112223344", "x", registrar=False)
        assert CircuitBreaker("falla").permitido() is False
        CircuitBreaker("falla").registrar_exito()  # limpiar para no contaminar otros tests


def test_notificar_whatsapp_best_effort(dos_tenants):
    from apps.mensajeria.services import notificar_whatsapp

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        assert notificar_whatsapp("", "x") is False  # sin teléfono
        assert notificar_whatsapp("5218112223344", "x") is True  # sandbox acepta


# ── F-B: config por UI (master switch global + preferencia por tenant) ───────

_CFG_XCC_ON = {"xcc_habilitado": True, "cb_umbral": 5, "cb_cooldown": 60, "cb_ventana": 300}
_CFG_XCC_OFF = {"xcc_habilitado": False, "cb_umbral": 5, "cb_cooldown": 60, "cb_ventana": 300}


def test_master_switch_apagado_salta_xcc(dos_tenants):
    """Con el Connector deshabilitado en global, listar 'xcc' en la preferencia no lo usa."""
    from apps.mensajeria.models import PreferenciaMensajeria

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        pref = PreferenciaMensajeria.cargar()
        pref.proveedores_orden = ["xcc", "sandbox"]
        pref.save()
        provs = router.proveedores_para(t1.schema_name, pref=pref, cfg=_CFG_XCC_OFF)
    # 'xcc' no está registrado ni habilitado → queda solo sandbox.
    assert [p.nombre for p in provs] == ["sandbox"]


def test_xcc_habilitado_se_incluye_en_orden(dos_tenants):
    """Con master switch ON y 'xcc' registrado (F-D), aparece en el orden del tenant."""
    from apps.mensajeria.models import PreferenciaMensajeria

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        pref = PreferenciaMensajeria.cargar()
        pref.proveedores_orden = ["xcc", "sandbox"]
        pref.save()
        provs = router.proveedores_para(t1.schema_name, pref=pref, cfg=_CFG_XCC_ON)
    assert [p.nombre for p in provs] == ["xcc", "sandbox"]


def test_preferencia_sin_configurar_usa_default(dos_tenants):
    """Sin PreferenciaMensajeria, el orden por defecto se mantiene (comportamiento previo a F-B)."""
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        provs = router.proveedores_para(t1.schema_name, pref=None, cfg=_CFG_XCC_OFF)
    # Sin ULTRAMSG_TOKEN en test → sandbox; el punto es que nunca queda vacío.
    assert len(provs) == 1


def test_failover_deshabilitado_solo_intenta_primario(dos_tenants, monkeypatch):
    from apps.mensajeria.models import PreferenciaMensajeria

    t1, _ = dos_tenants
    monkeypatch.setattr(
        router, "proveedores_para", lambda tenant, **kw: [_ProveedorFalla(), SandboxProvider()]
    )
    with schema_context(t1.schema_name):
        CircuitBreaker("falla").registrar_exito()  # estado limpio
        pref = PreferenciaMensajeria.cargar()
        pref.failover_habilitado = False
        pref.save()
        res = router.enviar("5218112223344", "hola", registrar=False)
        CircuitBreaker("falla").registrar_exito()  # no contaminar otros tests
    # Sin failover: no cae a sandbox aunque el primario falle.
    assert res.ok is False and res.proveedor == "falla"
