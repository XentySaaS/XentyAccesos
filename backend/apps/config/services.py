"""Servicio de auditoría — registra acciones en HistorialCambio.

Uso en ViewSets: heredar de ``AuditViewSetMixin`` antes de ``ModelViewSet``.
Uso puntual: llamar directamente a ``registrar()``.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import BitacoraAcceso, HistorialCambio

logger = logging.getLogger(__name__)


def registrar(
    descripcion: str,
    *,
    usuario=None,
    accion: str = HistorialCambio.Accion.ACTUALIZADO,
    modelo: str | None = None,
    modelo_id: int | None = None,
    antes: dict | None = None,
    despues: dict | None = None,
) -> HistorialCambio:
    """Inserta un registro de auditoría. Siempre append-only; nunca actualiza."""
    # HistorialCambio.usuario apunta a accounts.Usuario. Actores de otros contextos
    # (p. ej. CuentaProveedor) se registran sin FK de usuario para evitar ValueError.
    from apps.accounts.models import Usuario

    if usuario is not None and not isinstance(usuario, Usuario):
        usuario = None
    return HistorialCambio.objects.create(
        descripcion=descripcion,
        usuario=usuario,
        accion=accion,
        modelo=modelo,
        modelo_id=modelo_id,
        antes=antes,
        despues=despues,
    )


# ── Bitácora de accesos al sistema (autenticación) ────────────────────────────


def _ip_de(request) -> str | None:
    """IP del cliente respetando el proxy (Nginx reenvía X-Forwarded-For)."""
    if request is None:
        return None
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "")
    return ip or None


def _resumen_dispositivo(ua: str) -> str:
    """Etiqueta legible «Navegador · SO» a partir del User-Agent (heurística, sin dependencias)."""
    if not ua:
        return ""
    u = ua.lower()
    if "android" in u:
        so = "Android"
    elif "iphone" in u or "ipad" in u or "ios " in u:
        so = "iOS"
    elif "windows" in u:
        so = "Windows"
    elif "mac os" in u or "macintosh" in u:
        so = "macOS"
    elif "linux" in u:
        so = "Linux"
    else:
        so = ""
    if "edg/" in u:
        nav = "Edge"
    elif "opr/" in u or "opera" in u:
        nav = "Opera"
    elif "chrome" in u and "chromium" not in u:
        nav = "Chrome"
    elif "firefox" in u:
        nav = "Firefox"
    elif "safari" in u:
        nav = "Safari"
    else:
        nav = ""
    return " · ".join(p for p in (nav, so) if p)


def registrar_acceso(
    evento: str,
    *,
    contexto: str,
    request=None,
    actor=None,
    email: str = "",
    nombre: str = "",
    exito: bool = True,
    detalle: str = "",
) -> BitacoraAcceso | None:
    """Registra un evento de autenticación en la bitácora del tenant (best-effort; nunca lanza).

    Se salta en el schema ``public`` (la tabla es TENANT_APP; el super-admin del control plane no se
    audita aquí). El ``actor`` puede ser ``Usuario`` (→ FK) o ``CuentaProveedor`` (→ solo email/nombre).
    """
    from django.db import connection
    from django_tenants.utils import get_public_schema_name

    if connection.schema_name == get_public_schema_name():
        return None
    try:
        from apps.accounts.models import Usuario

        usuario = actor if isinstance(actor, Usuario) else None
        email = (email or getattr(actor, "email", "") or "").lower()
        nombre = nombre or getattr(actor, "nombre", "") or ""
        ua = (request.META.get("HTTP_USER_AGENT", "") if request else "")[:500]
        return BitacoraAcceso.objects.create(
            evento=evento,
            contexto=contexto,
            usuario=usuario,
            actor_email=email[:254],
            actor_nombre=nombre[:180],
            ip=_ip_de(request),
            dispositivo=_resumen_dispositivo(ua)[:180],
            user_agent=ua,
            exito=exito,
            detalle=detalle[:200],
        )
    except Exception:  # noqa: BLE001 — la bitácora nunca debe tumbar el login/logout
        logger.warning("No se pudo registrar el acceso al sistema (evento=%s)", evento)
        return None


def _safe(val: Any) -> Any:
    """Convierte valores no-JSON-serializables a str para almacenar en JSONField."""
    if val is None:
        return None
    if isinstance(val, str | int | float | bool):
        return val
    return str(val)


class AuditViewSetMixin:
    """Mixin para ModelViewSet que registra automáticamente creaciones, ediciones y bajas."""

    def perform_create(self, serializer):
        super().perform_create(serializer)
        obj = serializer.instance
        registrar(
            f"Creó {obj.__class__.__name__} «{obj}»",
            usuario=self.request.user,
            accion=HistorialCambio.Accion.CREADO,
            modelo=obj.__class__.__name__,
            modelo_id=obj.pk,
            despues={k: _safe(v) for k, v in serializer.validated_data.items()},
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        validated = serializer.validated_data

        # Captura estado ANTES de guardar (solo los campos que cambian)
        antes_dict: dict = {}
        for field_name in validated:
            if hasattr(instance, field_name):
                antes_dict[field_name] = _safe(getattr(instance, field_name))

        super().perform_update(serializer)
        obj = serializer.instance

        despues_dict = {k: _safe(getattr(obj, k, None)) for k in antes_dict}

        # Descripción legible: solo los campos que cambiaron
        cambios = [
            f"{k}: '{v}' → '{despues_dict[k]}'"
            for k, v in antes_dict.items()
            if str(v) != str(despues_dict.get(k))
        ]
        desc = f"Actualizó {obj.__class__.__name__} «{obj}»"
        if cambios:
            desc += " — " + "; ".join(cambios)

        registrar(
            desc,
            usuario=self.request.user,
            accion=HistorialCambio.Accion.ACTUALIZADO,
            modelo=obj.__class__.__name__,
            modelo_id=obj.pk,
            antes=antes_dict,
            despues=despues_dict,
        )

    def perform_destroy(self, instance):
        registrar(
            f"Eliminó {instance.__class__.__name__} «{instance}» (id={instance.pk})",
            usuario=self.request.user,
            accion=HistorialCambio.Accion.ELIMINADO,
            modelo=instance.__class__.__name__,
            modelo_id=instance.pk,
        )
        super().perform_destroy(instance)
