"""Cliente firmado para operaciones de sesión del XCC (proxy autenticado desde las SPAs).

Las SPAs **nunca** hablan directo con el XCC ni conocen el secreto HMAC: el backend firma por ellas.
Lee ``ConfiguracionConnector`` (``url_base`` + ``hmac_secret``, schema public), firma con el mismo
esquema que ``ConnectorProvider`` (F-D) y hace la petición. Devuelve ``RespuestaXCC(status, data)`` o
lanza ``ConnectorNoDisponible`` (no configurado/habilitado o sin respuesta).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass

from .connector_provider import _firmar  # reutiliza exactamente la misma cadena de firma HMAC


class ConnectorNoDisponible(Exception):
    """El Connector no está configurado/habilitado o no respondió."""


@dataclass
class RespuestaXCC:
    status: int
    data: dict | list | None


def _config() -> dict:
    from django_tenants.utils import get_public_schema_name, schema_context

    from apps.tenants.models import ConfiguracionConnector

    with schema_context(get_public_schema_name()):
        cfg = ConfiguracionConnector.objects.first()
        if not cfg or not cfg.habilitado or not cfg.url_base or not cfg.hmac_secret:
            raise ConnectorNoDisponible("El Connector no está habilitado o configurado.")
        return {
            "url_base": cfg.url_base.rstrip("/"),
            "secret": cfg.hmac_secret,
            "timeout_s": max(1.0, cfg.timeout_ms / 1000),
        }


def solicitar(
    tenant: str,
    method: str,
    path: str,
    body_obj: dict | None = None,
    connection_id: str | None = None,
) -> RespuestaXCC:
    """Petición firmada al XCC en nombre de un tenant. ``path`` sin query (p. ej. ``/v1/status``)."""
    cfg = _config()
    body = json.dumps(body_obj).encode("utf-8") if body_obj is not None else b""
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex
    firma = _firmar(cfg["secret"], method, path, tenant, ts, nonce, body)

    headers = {
        "Content-Type": "application/json",
        "X-XCC-Tenant": tenant,
        "X-XCC-Timestamp": ts,
        "X-XCC-Nonce": nonce,
        "X-XCC-Signature": firma,
    }
    if connection_id:
        headers["X-XCC-Connection"] = connection_id  # pista de ruteo sticky (no va en la firma)

    import requests

    try:
        resp = requests.request(
            method,
            f"{cfg['url_base']}{path}",
            data=body or None,
            headers=headers,
            timeout=cfg["timeout_s"],
        )
    except Exception as exc:  # noqa: BLE001 — red caída → mensaje claro para la UI; detalle al log
        import logging

        logging.getLogger(__name__).warning(
            "Connector inalcanzable en %s: %s", cfg["url_base"], exc
        )
        raise ConnectorNoDisponible(
            "No se pudo contactar al Connector. Verifica que esté encendido y la URL en «Comunicaciones»."
        ) from exc

    try:
        data = resp.json()
    except ValueError:
        data = None
    return RespuestaXCC(status=resp.status_code, data=data)
