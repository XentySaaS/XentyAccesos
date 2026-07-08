"""Router de mensajería con failover (ARQUITECTURA_CONNECTOR §6/§9).

Único orquestador de envío del sistema principal. Selecciona los proveedores del tenant leyendo su
``PreferenciaMensajeria`` (schema del tenant) y el master switch global ``ConfiguracionConnector``
(schema public); respeta el circuit breaker por proveedor, aplica reintentos y **failover** al
siguiente proveedor, y registra el intento. Nunca lanza: devuelve ``ResultadoEnvio``.

Con el Connector deshabilitado (o sin implementar), el único proveedor efectivo sigue siendo UltraMsg
(o Sandbox), así que el comportamiento es idéntico al de antes de F-B. El Connector se enchufa en F-D
registrándolo en ``proveedores.registro_proveedores`` — sin tocar este archivo ni el dominio.
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from .breaker import CircuitBreaker
from .proveedores import (
    ProveedorMensajeria,
    ResultadoEnvio,
    SandboxProvider,
    UltraMsgProvider,
    registro_proveedores,
)

# TTL corto del snapshot de config global: evita golpear el schema public en cada destinatario de una
# campaña, y a la vez propaga cambios del super-admin (habilitar/apagar el Connector) en segundos.
_CACHE_CONNECTOR = "connector:config"
_CACHE_TTL = 20


def _mascara(telefono: str) -> str:
    tel = "".join(ch for ch in telefono if ch.isdigit())
    return f"****{tel[-4:]}" if len(tel) >= 4 else "****"


def _config_connector() -> dict:
    """Snapshot (cacheado) de la config global del Connector, leído del schema public."""
    cached = cache.get(_CACHE_CONNECTOR)
    if cached is not None:
        return cached
    from apps.tenants.models import ConfiguracionConnector

    with schema_context(get_public_schema_name()):
        cfg = ConfiguracionConnector.objects.first()
        snap = {
            "xcc_habilitado": bool(cfg and cfg.habilitado),
            "cb_umbral": cfg.cb_umbral if cfg else 5,
            "cb_cooldown": cfg.cb_cooldown if cfg else 60,
            "cb_ventana": cfg.cb_ventana if cfg else 300,
        }
    cache.set(_CACHE_CONNECTOR, snap, _CACHE_TTL)
    return snap


def _breaker(nombre: str, cfg: dict) -> CircuitBreaker:
    return CircuitBreaker(
        nombre, umbral=cfg["cb_umbral"], cooldown=cfg["cb_cooldown"], ventana=cfg["cb_ventana"]
    )


def _preferencia():
    """``PreferenciaMensajeria`` del tenant actual, o ``None`` si aún no se configuró."""
    from .models import PreferenciaMensajeria

    return PreferenciaMensajeria.objects.first()


def _orden_default() -> list[str]:
    """Orden sensato cuando el tenant no fijó preferencia: UltraMsg si hay credencial, si no Sandbox."""
    return [UltraMsgProvider.nombre] if settings.ULTRAMSG_TOKEN else [SandboxProvider.nombre]


def proveedores_para(
    tenant: str, *, pref=None, cfg: dict | None = None
) -> list[ProveedorMensajeria]:
    """Proveedores instanciados en el orden efectivo del tenant.

    Precedencia (ARQUITECTURA_CONNECTOR §8): master switch global → preferencia del tenant. Filtra a
    las claves con implementación registrada y salta ``xcc`` si el Connector no está habilitado en
    global. Si nada resuelve, cae al proveedor por defecto (comportamiento previo a F-B).
    """
    cfg = cfg or _config_connector()
    registro = registro_proveedores()
    orden = list(pref.proveedores_orden) if (pref and pref.proveedores_orden) else _orden_default()

    provs: list[ProveedorMensajeria] = []
    for clave in orden:
        if clave == "xcc" and not cfg["xcc_habilitado"]:
            continue  # master switch global apagado → el Connector nunca se usa
        cls = registro.get(clave)
        if cls is not None:
            provs.append(cls())
    if not provs:  # preferencia inválida o proveedores no disponibles → fallback seguro
        clave = _orden_default()[0]
        provs = [registro[clave]()]
    return provs


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
    reintentos: int | None = None,
    registrar: bool = True,
) -> ResultadoEnvio:
    """Envía por el primer proveedor sano; ante fallo reintenta y hace failover al siguiente.

    ``reintentos`` y el failover se toman de ``PreferenciaMensajeria`` del tenant; pasar ``reintentos``
    explícito lo sobreescribe. Con ``failover_habilitado=False`` solo se intenta el primer proveedor.
    """
    cfg = _config_connector()
    pref = _preferencia()
    provs = proveedores_para(connection.schema_name, pref=pref, cfg=cfg)
    if pref and not pref.failover_habilitado:
        provs = provs[:1]  # sin failover: solo el proveedor primario
    if reintentos is None:
        reintentos = pref.reintentos if pref else 1

    ultimo = ResultadoEnvio(ok=False, proveedor="ninguno", error="Sin proveedores configurados.")
    for prov in provs:
        cb = _breaker(prov.nombre, cfg)
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
