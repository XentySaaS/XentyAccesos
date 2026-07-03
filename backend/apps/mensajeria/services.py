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
        """Envía texto; si ``archivo`` es una URL pública, manda un documento con caption.

        UltraMsg recibe el adjunto por URL (no subida), por eso ``archivo`` debe ser una URL
        alcanzable desde internet. Si no lo es (dev/localhost), el envío degrada a texto.
        """
        import requests

        base = f"https://api.ultramsg.com/{settings.ULTRAMSG_INSTANCE_ID}"
        if archivo:
            resp = requests.post(
                f"{base}/messages/document",
                data={"token": settings.ULTRAMSG_TOKEN, "to": telefono,
                      "document": archivo, "filename": archivo.rsplit("/", 1)[-1], "caption": cuerpo},
                timeout=20,
            )
        else:
            resp = requests.post(
                f"{base}/messages/chat",
                data={"token": settings.ULTRAMSG_TOKEN, "to": telefono, "body": cuerpo},
                timeout=15,
            )
        resp.raise_for_status()
        return str(resp.json().get("id", ""))


def obtener_whatsapp():
    return UltraMsgWhatsApp() if settings.ULTRAMSG_TOKEN else SandboxWhatsApp()


def notificar_whatsapp(telefono: str | None, cuerpo: str, archivo=None) -> bool:
    """Envía una notificación por WhatsApp si el destinatario tiene teléfono (best-effort).

    Regla del producto: toda notificación (usuario/proveedor/empleado/asistente) se manda también
    por WhatsApp cuando la persona tiene número. Punto único para actuales y futuras notificaciones.
    Nunca propaga errores (no debe bloquear la operación); devuelve True si se intentó el envío.
    """
    import logging

    tel = (telefono or "").strip()
    if not tel:
        return False
    try:
        obtener_whatsapp().enviar(tel, cuerpo, archivo)
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort
        logging.getLogger(__name__).warning("WhatsApp no enviado a %s: %s", tel, exc)
        return False


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

    # Adjunto (opcional): UltraMsg lo recibe por URL pública. Se arma con MEDIA_PUBLIC_BASE_URL
    # (dominio público del despliegue); si no está configurada, se envía solo texto.
    archivo_url = None
    if mensaje.archivo:
        base = getattr(settings, "MEDIA_PUBLIC_BASE_URL", "") or ""
        if base:
            archivo_url = base.rstrip("/") + mensaje.archivo.url

    destinatarios = list(mensaje.destinatarios.filter(estado=DestinatarioMensaje.Estado.PENDIENTE))
    total = len(destinatarios) or 1
    enviados = fallidos = 0
    for i, dest in enumerate(destinatarios, start=1):
        try:
            dest.external_id = cliente.enviar(dest.empleado.telefono or "", mensaje.cuerpo, archivo_url)
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
