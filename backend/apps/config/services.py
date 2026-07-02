"""Servicio de auditoría — registra acciones en HistorialCambio.

Uso en ViewSets: heredar de ``AuditViewSetMixin`` antes de ``ModelViewSet``.
Uso puntual: llamar directamente a ``registrar()``.
"""
from __future__ import annotations

from typing import Any

from .models import HistorialCambio


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


def _safe(val: Any) -> Any:
    """Convierte valores no-JSON-serializables a str para almacenar en JSONField."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
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
