"""Códigos de respaldo (recovery codes): 2º factor alternativo cuando el MFA está activo.

Si el usuario no puede usar su TOTP ni su llave, un código de respaldo de **un solo uso** completa
la sesión MFA pendiente. Se generan 10 a la vez y se muestran EN CLARO **una sola vez**; en la BD
solo vive su **HASH** (Argon2, el mismo esquema que las contraseñas — ``make_password``), nunca el
código plano. Cada código se marca ``usado_en`` al consumirse y no se reutiliza.

Patrón actor-agnóstico (como WebAuthn): ``CodigoRespaldoBase`` abstracto + subclase por actor con el
mismo ``related_name="codigos_respaldo"``, para que los endpoints operen sobre
``request.user.codigos_respaldo`` sin conocer el modelo concreto.
"""

from __future__ import annotations

import re
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

TOTAL_CODIGOS = 10
_GRUPOS = 3
_LARGO_GRUPO = 4
# Alfabeto sin caracteres ambiguos (sin 0/O/1/I/L) para que sean legibles al transcribirlos.
# 30 símbolos × 12 posiciones ≈ 2^58 de entropía por código.
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class CodigoRespaldoBase(models.Model):
    """Un código de respaldo de un solo uso. La subclase concreta añade el FK al actor."""

    codigo_hash = models.CharField(max_length=255)  # Argon2; jamás el código en claro
    usado_en = models.DateTimeField(null=True, blank=True, db_index=True)  # null = disponible
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["creado"]


def _normalizar(codigo: str) -> str:
    """Quita separadores y pasa a mayúsculas: se acepta el código con o sin guiones/espacios."""
    return re.sub(r"[^A-Za-z0-9]", "", codigo or "").upper()


def _generar_uno() -> str:
    cuerpo = "".join(secrets.choice(_ALFABETO) for _ in range(_LARGO_GRUPO * _GRUPOS))
    return "-".join(cuerpo[i : i + _LARGO_GRUPO] for i in range(0, len(cuerpo), _LARGO_GRUPO))


def generar_codigos() -> list[str]:
    """10 códigos nuevos EN CLARO, formato XXXX-XXXX-XXXX (CSPRNG: ``secrets``)."""
    return [_generar_uno() for _ in range(TOTAL_CODIGOS)]


def hash_codigo(codigo: str) -> str:
    return make_password(_normalizar(codigo))


def disponibles(manager) -> int:
    return manager.filter(usado_en__isnull=True).count()


def total(manager) -> int:
    return manager.count()


def regenerar(manager) -> list[str]:
    """Invalida los códigos previos del actor y crea un set nuevo. Devuelve los 10 EN CLARO (única vez)."""
    manager.all().delete()
    codigos = generar_codigos()
    for c in codigos:
        manager.create(codigo_hash=hash_codigo(c))  # el related manager fija el FK al actor
    return codigos


def consumir(manager, codigo: str) -> bool:
    """Valida un código NO usado y lo marca como usado. ``check_password`` compara en tiempo constante.

    Devuelve True si un código disponible coincidió (y quedó consumido); False en cualquier otro caso.
    """
    objetivo = _normalizar(codigo)
    if not objetivo:
        return False
    for c in manager.filter(usado_en__isnull=True):
        if check_password(objetivo, c.codigo_hash):
            c.usado_en = timezone.now()
            c.save(update_fields=["usado_en"])
            return True
    return False
