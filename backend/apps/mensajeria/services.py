"""WhatsApp (UltraMsg) tras interfaz, segmentación de campañas y procesamiento de envío.

Credenciales por entorno (REMEDIATION §C2); modo sandbox sin token. El envío real corre por Celery
con reintentos; aquí vive la lógica pura (``procesar_envio``) para poder probarla sin worker.
"""
from __future__ import annotations

import uuid

from django.conf import settings

from .models import DestinatarioMensaje, Mensaje


class SandboxWhatsApp:
    """No envía nada real; devuelve un id simulado (dev/test)."""

    def enviar(self, telefono: str, cuerpo: str, archivo=None) -> str:
        return f"sandbox-{uuid.uuid4().hex[:12]}"


class UltraMsgWhatsApp:
    def enviar(self, telefono: str, cuerpo: str, archivo=None) -> str:
        import requests

        url = f"https://api.ultramsg.com/{settings.ULTRAMSG_INSTANCE_ID}/messages/chat"
        resp = requests.post(
            url, data={"token": settings.ULTRAMSG_TOKEN, "to": telefono, "body": cuerpo}, timeout=15
        )
        resp.raise_for_status()
        return str(resp.json().get("id", ""))


def obtener_whatsapp():
    return UltraMsgWhatsApp() if settings.ULTRAMSG_TOKEN else SandboxWhatsApp()


def resolver_destinatarios(segmento: str, segmento_id=None):
    """Empleados objetivo según el segmento de la campaña."""
    from apps.empleados.models import Empleado
    from apps.eventos.models import EmpleadoEventoProveedor

    if segmento == Mensaje.Segmento.EVENTO:
        ids = EmpleadoEventoProveedor.objects.filter(
            evento_proveedor__evento_id=segmento_id
        ).values_list("empleado_id", flat=True)
        return Empleado.objects.filter(id__in=ids)
    if segmento == Mensaje.Segmento.RECINTO:
        ids = EmpleadoEventoProveedor.objects.filter(
            evento_proveedor__evento__recinto_id=segmento_id
        ).values_list("empleado_id", flat=True)
        return Empleado.objects.filter(id__in=ids)
    if segmento in (Mensaje.Segmento.TODOS_EVENTOS, Mensaje.Segmento.TODOS_RECINTOS):
        return Empleado.objects.all()
    return Empleado.objects.none()


def crear_destinatarios(mensaje: Mensaje):
    empleados = resolver_destinatarios(mensaje.segmento, mensaje.segmento_id)
    DestinatarioMensaje.objects.bulk_create(
        [DestinatarioMensaje(mensaje=mensaje, empleado=e) for e in empleados]
    )


def procesar_envio(mensaje_id: int) -> dict:
    """Envía la campaña a sus destinatarios pendientes y actualiza estado/progreso."""
    cliente = obtener_whatsapp()
    mensaje = Mensaje.objects.get(id=mensaje_id)
    mensaje.estado = Mensaje.Estado.EN_PROGRESO
    mensaje.save(update_fields=["estado"])

    destinatarios = list(mensaje.destinatarios.filter(estado=DestinatarioMensaje.Estado.PENDIENTE))
    total = len(destinatarios) or 1
    enviados = fallidos = 0
    for i, dest in enumerate(destinatarios, start=1):
        try:
            dest.external_id = cliente.enviar(dest.empleado.telefono or "", mensaje.cuerpo)
            dest.estado = DestinatarioMensaje.Estado.ENVIADO
            enviados += 1
        except Exception:
            dest.estado = DestinatarioMensaje.Estado.FALLIDO
            fallidos += 1
        dest.save(update_fields=["estado", "external_id"])
        mensaje.progreso = round(i / total * 100, 2)
        mensaje.save(update_fields=["progreso"])

    mensaje.estado = Mensaje.Estado.COMPLETADO
    mensaje.save(update_fields=["estado"])
    return {"enviados": enviados, "fallidos": fallidos}
