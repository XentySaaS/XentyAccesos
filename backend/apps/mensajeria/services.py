"""Mensajería: segmentación de campañas y procesamiento de envío.

El envío pasa SIEMPRE por ``apps.mensajeria.router`` (proveedores tras interfaz + failover +
circuit breaker). Aquí solo vive la lógica de campañas y el helper de notificación. El envío real
corre por Celery con reintentos.
"""

from __future__ import annotations

from django.conf import settings

from common.phone import formato_whatsapp_mx

from . import router
from .models import DestinatarioMensaje, Mensaje


def notificar_whatsapp(telefono: str | None, cuerpo: str, archivo=None) -> bool:
    """Notificación por WhatsApp si el destinatario tiene teléfono (best-effort, punto único).

    Regla del producto: toda notificación (usuario/proveedor/empleado/asistente) se manda también
    por WhatsApp cuando la persona tiene número. El teléfono se guarda a 10 dígitos (sin lada); aquí
    se antepone la lada mexicana para el destino (punto único, ``common.phone``). Un número inválido
    (no 10 dígitos) se omite en vez de mandarse. Delega en el Router (nunca lanza); devuelve True si
    el envío fue aceptado por algún proveedor.
    """
    tel = formato_whatsapp_mx(telefono)
    if not tel:
        return False
    return router.enviar(tel, cuerpo, archivo, reintentos=1, registrar=True).ok


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
    """Envía la campaña a sus destinatarios pendientes (vía Router) y actualiza estado/progreso."""
    mensaje = Mensaje.objects.get(id=mensaje_id)
    mensaje.estado = Mensaje.Estado.EN_PROGRESO
    mensaje.save(update_fields=["estado"])

    # Adjunto (opcional): el proveedor lo recibe por URL pública (MEDIA_PUBLIC_BASE_URL). Sin ella,
    # se envía solo texto.
    archivo_url = None
    if mensaje.archivo:
        base = getattr(settings, "MEDIA_PUBLIC_BASE_URL", "") or ""
        if base:
            archivo_url = base.rstrip("/") + mensaje.archivo.url

    destinatarios = list(mensaje.destinatarios.filter(estado=DestinatarioMensaje.Estado.PENDIENTE))
    total = len(destinatarios) or 1
    enviados = fallidos = 0
    for i, dest in enumerate(destinatarios, start=1):
        # El ledger de campaña es DestinatarioMensaje; no duplicar en RegistroEnvio (registrar=False).
        # El teléfono va con lada mexicana; sin 10 dígitos válidos se marca fallido sin llamar al Router.
        tel = formato_whatsapp_mx(dest.empleado.telefono)
        res = router.enviar(tel, mensaje.cuerpo, archivo_url, registrar=False) if tel else None
        if res and res.ok:
            dest.estado = DestinatarioMensaje.Estado.ENVIADO
            enviados += 1
        else:
            dest.estado = DestinatarioMensaje.Estado.FALLIDO
            fallidos += 1
        dest.external_id = res.external_id if res else ""
        dest.proveedor = res.proveedor if res else ""
        dest.save(update_fields=["estado", "external_id", "proveedor"])
        mensaje.progreso = round(i / total * 100, 2)
        mensaje.save(update_fields=["progreso"])

    mensaje.estado = Mensaje.Estado.COMPLETADO
    mensaje.save(update_fields=["estado"])
    return {"enviados": enviados, "fallidos": fallidos}
