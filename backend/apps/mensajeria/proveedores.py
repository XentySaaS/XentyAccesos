"""Proveedores de mensajería detrás de una interfaz estable (ARQUITECTURA_CONNECTOR §4.1/§6).

El sistema principal habla con ``ProveedorMensajeria``; jamás con una implementación concreta. Hoy
existe UltraMsg (principal) y Sandbox (dev). El Connector (XCC) se sumará como un proveedor más en
F-D **sin tocar** al dominio ni al Router.

Contrato clave: ``enviar()`` **nunca lanza**; devuelve ``ResultadoEnvio`` (ok/error) para que el
Router decida reintento/failover.
"""

from __future__ import annotations

import base64
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


@dataclass
class AdjuntoWhatsApp:
    """Adjunto de WhatsApp cargado como bytes (gafete generado, protocolo almacenado…).

    Se envía como **base64** al proveedor (el Connector lo acepta nativamente; UltraMsg vía su API
    de imagen/documento). Así no hace falta exponer en una URL pública un archivo con QR firmado.
    """

    nombre_archivo: str
    contenido: bytes
    mimetype: str
    caption: str = ""

    @property
    def es_imagen(self) -> bool:
        return self.mimetype.startswith("image/")

    def b64(self) -> str:
        return base64.b64encode(self.contenido).decode("ascii")


class ProveedorMensajeria(Protocol):
    nombre: str

    def enviar(
        self,
        telefono: str,
        cuerpo: str,
        archivo: str | None = None,
        *,
        adjunto: AdjuntoWhatsApp | None = None,
    ) -> ResultadoEnvio: ...


class SandboxProvider:
    """No envía nada real; simula un id (dev/test)."""

    nombre = "sandbox"

    def enviar(
        self,
        telefono: str,
        cuerpo: str,
        archivo: str | None = None,
        *,
        adjunto: AdjuntoWhatsApp | None = None,
    ) -> ResultadoEnvio:
        return ResultadoEnvio(
            ok=True, proveedor=self.nombre, external_id=f"sandbox-{uuid.uuid4().hex[:12]}"
        )


class UltraMsgProvider:
    """Proveedor principal (nube). Envía texto; un adjunto (bytes) va como imagen/documento base64,
    o un ``archivo`` (URL pública) como documento."""

    nombre = "ultramsg"

    def enviar(
        self,
        telefono: str,
        cuerpo: str,
        archivo: str | None = None,
        *,
        adjunto: AdjuntoWhatsApp | None = None,
    ) -> ResultadoEnvio:
        import requests

        base = f"https://api.ultramsg.com/{settings.ULTRAMSG_INSTANCE_ID}"
        try:
            if adjunto is not None:
                # UltraMsg acepta base64 en los campos image/document.
                if adjunto.es_imagen:
                    endpoint, campo = "image", "image"
                else:
                    endpoint, campo = "document", "document"
                data = {
                    "token": settings.ULTRAMSG_TOKEN,
                    "to": telefono,
                    campo: adjunto.b64(),
                    "caption": cuerpo,
                }
                if not adjunto.es_imagen:
                    data["filename"] = adjunto.nombre_archivo
                resp = requests.post(f"{base}/messages/{endpoint}", data=data, timeout=25)
            elif archivo:
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
