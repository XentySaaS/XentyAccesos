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
        router, "proveedores_para", lambda tenant: [_ProveedorFalla(), SandboxProvider()]
    )
    with schema_context(t1.schema_name):
        CircuitBreaker("falla").registrar_exito()  # estado limpio
        res = router.enviar("5218112223344", "hola", registrar=False)
    assert res.ok and res.proveedor == "sandbox"


def test_circuit_breaker_abre_tras_umbral(dos_tenants, monkeypatch):
    t1, _ = dos_tenants
    monkeypatch.setattr(router, "proveedores_para", lambda tenant: [_ProveedorFalla()])
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
