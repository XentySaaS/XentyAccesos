"""Teléfonos mexicanos: formato canónico de 10 dígitos + formato para WhatsApp.

Xenty opera **solo en México**, así que el formato canónico que se almacena es de **10 dígitos,
sin lada**. Este módulo es el único lugar que:

  - normaliza lo que captura el usuario a esos 10 dígitos (quitando lada, espacios, ``+``…), y
  - antepone la lada mexicana **únicamente al enviar por WhatsApp** (nunca se guarda con lada).

Cambiar el formato de envío (p. ej. quitar el ``1`` de móvil) se hace en un solo sitio:
:func:`formato_whatsapp_mx`.
"""

from __future__ import annotations

import re

from rest_framework import serializers

_NO_DIGITOS = re.compile(r"\D+")


def solo_digitos(valor: str | None) -> str:
    """Devuelve solo los dígitos de ``valor`` (quita espacios, guiones, ``+``, paréntesis…)."""
    return _NO_DIGITOS.sub("", valor or "")


def normalizar_telefono(valor: str | None) -> str:
    """Normaliza a los 10 dígitos canónicos (México), sin lada.

    Quita la lada de país si viene incluida (``52`` o ``52`` + ``1`` de móvil). Devuelve ``""``
    cuando, tras limpiar, no quedan exactamente 10 dígitos (número inválido/incompleto).

    Ejemplos::

        "8112223344"        -> "8112223344"
        "55 1234 5678"      -> "5512345678"
        "+52 811 222 3344"  -> "8112223344"
        "5218112223344"     -> "8112223344"
        "123"               -> ""
    """
    d = solo_digitos(valor)
    if len(d) == 13 and d.startswith("521"):
        d = d[3:]
    elif len(d) == 12 and d.startswith("52"):
        d = d[2:]
    return d if len(d) == 10 else ""


def formato_whatsapp_mx(valor: str | None) -> str:
    """Formato de destino para WhatsApp México: ``52`` + ``1`` (móvil) + 10 dígitos.

    Es el JID canónico que WhatsApp usa para México (p. ej. ``5218112223344``); tanto UltraMsg
    como el Connector lo aceptan y el Connector lo resuelve vía ``onWhatsApp``. Devuelve ``""`` si
    el teléfono no es válido (no son 10 dígitos), para que el emisor lo omita en vez de mandar un
    número imposible de entregar.
    """
    diez = normalizar_telefono(valor)
    return f"521{diez}" if diez else ""


class TelefonoField(serializers.CharField):
    """Campo DRF de teléfono: acepta lo que capture el usuario y lo guarda como 10 dígitos.

    Normaliza con :func:`normalizar_telefono` (quita lada/espacios). Rechaza con un error claro lo
    que no sean 10 dígitos válidos. Deja pasar vacío/nulo si el campo lo permite (``allow_blank`` /
    ``allow_null``). No fija ``max_length`` para no rechazar la entrada cruda con lada/espacios
    antes de normalizarla.
    """

    def to_internal_value(self, data):
        valor = super().to_internal_value(data)
        if not valor or not valor.strip():
            return ""
        tel = normalizar_telefono(valor)
        if not tel:
            raise serializers.ValidationError("Ingresa un teléfono de 10 dígitos (sin lada).")
        return tel
