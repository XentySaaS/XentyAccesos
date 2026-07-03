"""Redacción de PII para logs y Sentry (REMEDIACION §A7).

Evita que RFC, CURP, email, NSS o datos de INE lleguen a los logs o a Sentry en claro.
"""

from __future__ import annotations

import logging
import re

_PATRONES = [
    (re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", re.I), "[RFC]"),
    (re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", re.I), "[CURP]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
]

CLAVES_PII = {
    "curp",
    "rfc",
    "nss",
    "ine_data",
    "numero_identificacion",
    "password",
    "email",
    "telefono",
    "token",
    "secret",
    "mfa_totp_secret",
}


def redactar_texto(texto: str) -> str:
    for patron, reemplazo in _PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto


def redactar(valor):
    """Redacta recursivamente PII en dicts/listas/strings."""
    if isinstance(valor, dict):
        return {
            k: ("[REDACTED]" if k.lower() in CLAVES_PII else redactar(v)) for k, v in valor.items()
        }
    if isinstance(valor, list | tuple):
        return [redactar(v) for v in valor]
    if isinstance(valor, str):
        return redactar_texto(valor)
    return valor


def procesador_structlog(logger, method_name, event_dict):
    """Processor de structlog: redacta PII de cada evento antes de emitir."""
    return redactar(event_dict)


class RedaccionPIIFilter(logging.Filter):
    """Filtro de logging estándar: redacta PII (RFC/CURP/email) del mensaje ya formateado.

    Se cablea en ``LOGGING`` (REMEDIACION §A7). Cubre las llamadas ``logging.getLogger`` existentes
    sin refactorizarlas: aplica la redacción sobre ``record.getMessage()`` antes de emitir.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redactar_texto(record.getMessage())
            record.args = ()
        except Exception:
            pass
        return True


def scrub_event(event, hint):
    """``before_send`` de Sentry: redacta PII del evento antes de enviarlo."""
    try:
        if event.get("request", {}).get("data"):
            event["request"]["data"] = redactar(event["request"]["data"])
        if event.get("extra"):
            event["extra"] = redactar(event["extra"])
    except Exception:
        pass
    return event
