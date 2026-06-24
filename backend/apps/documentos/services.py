"""Regla central ``checkdocs`` (SAR_FUNCIONALIDADES §5.3).

Pura y testeable. F3 la invoca con los grupos requeridos del evento para sincronizar
``EmpleadoEventoProveedor.statusdocs``.
"""
from __future__ import annotations

from collections.abc import Iterable

from .models import DocumentoEmpleado, TipoDocumento

# type_validation
AL_MENOS_UNO = 0
TODOS = 1


def cumple_requisitos(empleado, requisitos: Iterable[tuple[int, int]]) -> bool:
    """¿El empleado cumple los grupos requeridos?

    ``requisitos`` = iterable de ``(grupo_id, type_validation)``:
    - ``AL_MENOS_UNO`` (0): basta un documento VERIFICADO del grupo.
    - ``TODOS`` (1): todos los tipos activos del grupo deben estar VERIFICADOS.
    """
    verif = DocumentoEmpleado.Estado.VERIFICADO
    for grupo_id, tipo_validacion in requisitos:
        verificados = set(
            DocumentoEmpleado.objects.filter(
                empleado=empleado, tipo_documento__grupo_id=grupo_id, estado=verif
            ).values_list("tipo_documento_id", flat=True)
        )
        if tipo_validacion == TODOS:
            requeridos = set(
                TipoDocumento.objects.filter(grupo_id=grupo_id, activo=True).values_list("id", flat=True)
            )
            if not requeridos or not requeridos.issubset(verificados):
                return False
        else:  # AL_MENOS_UNO
            if not verificados:
                return False
    return True


def notificar_rechazo(documento) -> None:
    """Best-effort: avisa al proveedor que su documento fue rechazado (no bloquea la petición)."""
    from django.core.mail import send_mail

    cuenta = getattr(documento.empleado, "proveedor", None)
    email = getattr(cuenta, "email", None)
    if not email:
        return
    try:
        send_mail(
            "Documento rechazado",
            f"El documento '{documento.tipo_documento}' de {documento.empleado} fue rechazado. "
            f"Motivo: {documento.motivo_rechazo or 'no especificado'}.",
            None, [email], fail_silently=True,
        )
    except Exception:
        pass
