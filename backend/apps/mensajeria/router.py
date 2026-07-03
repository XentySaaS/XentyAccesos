"""Router de mensajería con failover (ARQUITECTURA_CONNECTOR §6/§9).

Único orquestador de envío del sistema principal. Selecciona los proveedores del tenant (por ahora
por configuración de entorno; en F-B leerá ``PreferenciaMensajeria`` del schema del tenant), respeta
el circuit breaker por proveedor, aplica reintentos y **failover** al siguiente proveedor, y registra
el intento. Nunca lanza: devuelve ``ResultadoEnvio``.

En F-A solo hay un proveedor efectivo (UltraMsg o Sandbox), pero toda la maquinaria de resiliencia
queda lista para enchufar el Connector en F-D sin tocar el dominio.
"""

from __future__ import annotations

from django.conf import settings
from django.db import connection

from .breaker import CircuitBreaker
from .proveedores import ProveedorMensajeria, ResultadoEnvio, SandboxProvider, UltraMsgProvider


def _mascara(telefono: str) -> str:
    tel = "".join(ch for ch in telefono if ch.isdigit())
    return f"****{tel[-4:]}" if len(tel) >= 4 else "****"


def proveedores_para(tenant: str) -> list[ProveedorMensajeria]:
    """Orden de proveedores del tenant. F-A: global por entorno. F-B: ``PreferenciaMensajeria``."""
    if settings.ULTRAMSG_TOKEN:
        return [UltraMsgProvider()]
    return [SandboxProvider()]


def _registrar(telefono: str, res: ResultadoEnvio) -> None:
    from .models import RegistroEnvio

    try:
        RegistroEnvio.objects.create(
            destino_mascara=_mascara(telefono),
            proveedor=res.proveedor,
            ok=res.ok,
            external_id=res.external_id or None,
            error=res.error or None,
        )
    except Exception:  # noqa: BLE001 — el ledger nunca debe tumbar el envío
        pass


def enviar(
    telefono: str,
    cuerpo: str,
    archivo: str | None = None,
    *,
    reintentos: int = 1,
    registrar: bool = True,
) -> ResultadoEnvio:
    """Envía por el primer proveedor sano; ante fallo reintenta y hace failover al siguiente."""
    provs = proveedores_para(connection.schema_name)
    ultimo = ResultadoEnvio(ok=False, proveedor="ninguno", error="Sin proveedores configurados.")

    for prov in provs:
        cb = CircuitBreaker(prov.nombre)
        if not cb.permitido():
            ultimo = ResultadoEnvio(ok=False, proveedor=prov.nombre, error="circuit-open")
            continue
        for _ in range(max(1, reintentos + 1)):
            res = prov.enviar(telefono, cuerpo, archivo)
            if res.ok:
                cb.registrar_exito()
                if registrar:
                    _registrar(telefono, res)
                return res
            cb.registrar_fallo()
            ultimo = res

    if registrar:
        _registrar(telefono, ultimo)
    return ultimo
