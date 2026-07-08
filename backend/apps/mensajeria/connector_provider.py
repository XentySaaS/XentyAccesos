"""Cliente del Xenty Communication Connector (XCC) como ``ProveedorMensajeria`` (F-D).

Es *un proveedor más* detrás del Router: habla REST+HMAC con el servicio Node/Baileys (repo separado
``xenty-connector``). Lee la config global ``ConfiguracionConnector`` (schema public): ``url_base``,
``hmac_secret`` (Fernet, se descifra al leer) y ``timeout_ms``. **Nunca lanza**: ante cualquier fallo
(sin config, red, HTTP≠202) devuelve ``ok=False`` para que el Router haga failover a UltraMsg.

La cadena de firma DEBE coincidir byte a byte con la que valida el XCC
(``xenty-connector/src/hmac.ts``):

    HMAC_SHA256(secret, f"{METHOD}\\n{PATH}\\n{TENANT}\\n{TIMESTAMP}\\n{NONCE}\\n{SHA256_HEX(body)}")

Por eso se firma y se envía **exactamente el mismo cuerpo** (``data=body`` bytes, no ``json=``): así
el hash del cuerpo local es idéntico al que recomputa el servidor sobre los bytes recibidos.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from .proveedores import ResultadoEnvio

_MESSAGES_PATH = "/v1/messages"


def _firmar(
    secret: str, method: str, path: str, tenant: str, ts: str, nonce: str, body: bytes
) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    signing = f"{method.upper()}\n{path}\n{tenant}\n{ts}\n{nonce}\n{body_hash}"
    return hmac.new(secret.encode(), signing.encode(), hashlib.sha256).hexdigest()


class ConnectorProvider:
    """Proveedor de respaldo servido por el XCC. Selecciona ``connection_id`` (número) del tenant."""

    nombre = "xcc"

    def __init__(self, connection_id: str = "principal"):
        self.connection_id = connection_id

    def _config(self) -> dict | None:
        """Config global del Connector, o ``None`` si no está lista (deshabilitado/sin URL/sin secreto)."""
        from apps.tenants.models import ConfiguracionConnector

        with schema_context(get_public_schema_name()):
            cfg = ConfiguracionConnector.objects.first()
            if not cfg or not cfg.habilitado or not cfg.url_base or not cfg.hmac_secret:
                return None
            return {
                "url_base": cfg.url_base.rstrip("/"),
                "secret": cfg.hmac_secret,
                "timeout_s": max(1.0, cfg.timeout_ms / 1000),
            }

    def enviar(self, telefono: str, cuerpo: str, archivo: str | None = None) -> ResultadoEnvio:
        cfg = self._config()
        if cfg is None:
            return ResultadoEnvio(ok=False, proveedor=self.nombre, error="xcc-no-configurado")

        payload: dict = {
            "channel": "whatsapp",
            "connection_id": self.connection_id,
            "to": telefono,
        }
        if archivo:
            # El XCC descarga la media por URL; sin URL pública se manda solo texto.
            payload.update(
                type="document",
                media_url=archivo,
                filename=archivo.rsplit("/", 1)[-1],
                caption=cuerpo,
            )
        else:
            payload.update(type="text", text=cuerpo)

        # Bytes exactos que se firman y se envían (deben coincidir con lo que hashea el servidor).
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        tenant = connection.schema_name
        ts = str(int(time.time()))
        nonce = uuid.uuid4().hex
        firma = _firmar(cfg["secret"], "POST", _MESSAGES_PATH, tenant, ts, nonce, body)

        import requests

        try:
            resp = requests.post(
                f"{cfg['url_base']}{_MESSAGES_PATH}",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-XCC-Tenant": tenant,
                    "X-XCC-Timestamp": ts,
                    "X-XCC-Nonce": nonce,
                    "X-XCC-Signature": firma,
                },
                timeout=cfg["timeout_s"],
            )
        except Exception as exc:  # noqa: BLE001 — red caída → el Router hace failover con ok=False
            return ResultadoEnvio(ok=False, proveedor=self.nombre, error=f"xcc-red:{exc}")

        if resp.status_code == 202:
            try:
                external_id = str(resp.json().get("message_id") or "")
            except ValueError:
                external_id = ""
            return ResultadoEnvio(ok=True, proveedor=self.nombre, external_id=external_id)
        return ResultadoEnvio(ok=False, proveedor=self.nombre, error=f"xcc-http-{resp.status_code}")
