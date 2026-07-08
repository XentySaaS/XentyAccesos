"""Proveedores de mensajería detrás de una interfaz estable (ARQUITECTURA_CONNECTOR §4.1/§6).

El sistema principal habla con ``ProveedorMensajeria``; jamás con una implementación concreta. Hoy
existe UltraMsg (principal) y Sandbox (dev). El Connector (XCC) se sumará como un proveedor más en
F-D **sin tocar** al dominio ni al Router.

Contrato clave: ``enviar()`` **nunca lanza**; devuelve ``ResultadoEnvio`` (ok/error) para que el
Router decida reintento/failover.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings


@dataclass
class ResultadoEnvio:
    ok: bool
    proveedor: str
    external_id: str | None = None
    error: str | None = None


class ProveedorMensajeria(Protocol):
    nombre: str

    def enviar(self, telefono: str, cuerpo: str, archivo: str | None = None) -> ResultadoEnvio: ...


class SandboxProvider:
    """No envía nada real; simula un id (dev/test)."""

    nombre = "sandbox"

    def enviar(self, telefono: str, cuerpo: str, archivo: str | None = None) -> ResultadoEnvio:
        return ResultadoEnvio(
            ok=True, proveedor=self.nombre, external_id=f"sandbox-{uuid.uuid4().hex[:12]}"
        )


class UltraMsgProvider:
    """Proveedor principal (nube). Envía texto; con URL pública de archivo manda documento."""

    nombre = "ultramsg"

    def enviar(self, telefono: str, cuerpo: str, archivo: str | None = None) -> ResultadoEnvio:
        import requests

        base = f"https://api.ultramsg.com/{settings.ULTRAMSG_INSTANCE_ID}"
        try:
            if archivo:
                resp = requests.post(
                    f"{base}/messages/document",
                    data={
                        "token": settings.ULTRAMSG_TOKEN,
                        "to": telefono,
                        "document": archivo,
                        "filename": archivo.rsplit("/", 1)[-1],
                        "caption": cuerpo,
                    },
                    timeout=20,
                )
            else:
                resp = requests.post(
                    f"{base}/messages/chat",
                    data={"token": settings.ULTRAMSG_TOKEN, "to": telefono, "body": cuerpo},
                    timeout=15,
                )
            resp.raise_for_status()
            return ResultadoEnvio(
                ok=True, proveedor=self.nombre, external_id=str(resp.json().get("id", ""))
            )
        except Exception as exc:  # noqa: BLE001 — el Router decide failover con ok=False
            return ResultadoEnvio(ok=False, proveedor=self.nombre, error=str(exc))


def registro_proveedores() -> dict[str, type]:
    """Proveedores con implementación disponible, indexados por su clave (``nombre``).

    Punto único de extensión: sumar un proveedor = añadirlo aquí, sin tocar el Router ni el dominio
    (ARQUITECTURA_CONNECTOR §6). El Connector (``"xcc"``, F-D) queda registrado, pero el Router solo lo
    usa si el master switch global (``ConfiguracionConnector.habilitado``) está activo; si está
    apagado, ``proveedores_para`` lo salta aunque un tenant lo liste.
    """
    from .connector_provider import ConnectorProvider

    reg: dict[str, type] = {
        UltraMsgProvider.nombre: UltraMsgProvider,
        SandboxProvider.nombre: SandboxProvider,
        ConnectorProvider.nombre: ConnectorProvider,
    }
    return reg
