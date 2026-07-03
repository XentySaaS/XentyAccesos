"""Lógica edge: cola de comandos (long-poll) y validación de QR dentro del tenant del dispositivo.

Corrige C6 (filtro por dispositivo en pull/ack) y C7 (la validación corre en el tenant del
dispositivo; un QR de otro tenant se rechaza).
"""

from __future__ import annotations

from django_tenants.utils import get_public_schema_name, schema_context


def pull_comandos(device) -> list:
    """Devuelve los comandos PENDING del dispositivo y los marca SENT (long-poll pull)."""
    from apps.tenants.models import ComandoEdge

    with schema_context(get_public_schema_name()):
        pendientes = list(
            ComandoEdge.objects.filter(dispositivo=device, estado=ComandoEdge.Estado.PENDING)
        )
        ComandoEdge.objects.filter(id__in=[c.id for c in pendientes]).update(
            estado=ComandoEdge.Estado.SENT
        )
    return pendientes


def ack_comando(device, comando_id) -> int:
    """Marca ACK solo si el comando pertenece a ESTE dispositivo (corrige C6). Devuelve filas afectadas."""
    from apps.tenants.models import ComandoEdge

    with schema_context(get_public_schema_name()):
        return ComandoEdge.objects.filter(dispositivo=device, id=comando_id).update(
            estado=ComandoEdge.Estado.ACK
        )


def validar_qr_edge(device, qr: str) -> tuple[bool, str]:
    """Valida el QR dentro del tenant del dispositivo (C7): un QR de otro tenant se rechaza."""
    schema = device.tenant.schema_name
    with schema_context(schema):
        from apps.acceso.services import procesar_escaneo

        _, permitido, motivo = procesar_escaneo(qr, schema)
        return permitido, motivo
