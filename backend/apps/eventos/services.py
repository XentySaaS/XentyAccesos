"""Notificaciones del módulo de eventos (correo + WhatsApp), best-effort.

Replica el flujo del origen (SendNewEvent / SendWPEntry / SendWPCancelEvent / SendParking) reusando
el cliente de WhatsApp de ``apps.mensajeria`` y el correo de Django. Las notificaciones nunca
bloquean la operación: si fallan, se registran y la API responde igual (en dev, WhatsApp es sandbox
y el correo va a Mailpit).
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.mensajeria.services import obtener_whatsapp

logger = logging.getLogger(__name__)


def _enviar_whatsapp(telefono: str | None, cuerpo: str) -> None:
    if not telefono:
        return
    try:
        obtener_whatsapp().enviar(telefono, cuerpo)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("WhatsApp evento no enviado a %s: %s", telefono, exc)


def _enviar_correo(asunto: str, cuerpo: str, destino: str | None) -> None:
    if not destino:
        return
    try:
        send_mail(
            asunto, cuerpo,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@xenty.mx"),
            [destino], fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("Correo evento no enviado a %s: %s", destino, exc)


def notificar_invitacion(ep, *, nombre_tenant: str, panel_url: str | None = None) -> None:
    """Avisa al proveedor (correo + WhatsApp) que fue invitado a un evento."""
    proveedor = ep.proveedor
    evento = ep.evento
    responsable = (proveedor.nombre_responsable or proveedor.nombre or "").strip().title()
    panel = (panel_url or "").rstrip("/")
    enlace = f"{panel}/proveedores/eventos" if panel else "tu panel de proveedor"

    cuerpo = (
        f"Hola {responsable},\n\n"
        f"{nombre_tenant} te invitó al evento «{evento.nombre}».\n\n"
        f"Define el personal que asistirá desde la sección de Eventos en tu cuenta.\n"
    )
    if ep.requiere_parking and ep.cajones_parking:
        cuerpo += (
            f"\nSe te asignaron {ep.cajones_parking} cajón(es) de estacionamiento"
            f"{(' (' + ep.parking + ')') if ep.parking else ''}; "
            "descarga los pases desde tu cuenta.\n"
        )
    cuerpo += f"\nIngresa aquí: {enlace}\n\n— {nombre_tenant} · Xenty Acceso"

    asunto = f"Invitación al evento {evento.nombre} — {nombre_tenant}"
    _enviar_correo(asunto, cuerpo, proveedor.email_responsable or proveedor.email)
    _enviar_whatsapp(proveedor.telefono, cuerpo)


def notificar_invitacion_cancelada(ep, *, nombre_tenant: str) -> None:
    """Avisa al proveedor que su invitación a un evento fue retirada."""
    proveedor = ep.proveedor
    cuerpo = (
        f"La invitación al evento «{ep.evento.nombre}» de {nombre_tenant} ha sido cancelada.\n\n"
        f"— {nombre_tenant} · Xenty Acceso"
    )
    _enviar_whatsapp(proveedor.telefono, cuerpo)
    _enviar_correo(f"Invitación cancelada — {ep.evento.nombre}", cuerpo,
                   proveedor.email_responsable or proveedor.email)


def _resumen_evento(ep) -> str:
    """Línea legible con los datos del evento/invitación para notificaciones."""
    ev = ep.evento
    partes = [f"«{ev.nombre}» en {ev.recinto.nombre}"]
    fecha = ev.vigencia_inicio.strftime("%d/%m/%Y")
    if ev.hora_inicio:
        fecha += f" {ev.hora_inicio.strftime('%H:%M')}"
    partes.append(f"el {fecha}")
    if ep.zona_id:
        partes.append(f"zona {ep.zona.nombre}")
    if ep.acceso_id:
        partes.append(f"acceso {ep.acceso.nombre}")
    return ", ".join(partes)


def notificar_asignacion_empleado(asignacion, *, nombre_tenant: str) -> None:
    """Avisa al empleado (correo + WhatsApp) que fue asignado a un evento y cómo entrar."""
    empleado = asignacion.empleado
    ep = asignacion.evento_proveedor
    cuerpo = (
        f"Hola {empleado.nombre}, {nombre_tenant} te asignó al evento {_resumen_evento(ep)}.\n\n"
        f"Presenta tu gafete de acceso (QR) en el punto de acceso indicado."
    )
    _enviar_correo(f"Acceso a evento — {ep.evento.nombre}", cuerpo, empleado.email)
    _enviar_whatsapp(empleado.telefono, cuerpo)


def notificar_desasignacion_empleado(empleado, evento, *, nombre_tenant: str) -> None:
    """Avisa al empleado que su acceso al evento fue revocado."""
    cuerpo = (
        f"Hola {empleado.nombre}, tu acceso al evento «{evento.nombre}» de {nombre_tenant} "
        f"ha sido revocado."
    )
    _enviar_correo(f"Acceso revocado — {evento.nombre}", cuerpo, empleado.email)
    _enviar_whatsapp(empleado.telefono, cuerpo)


def recalcular_status_asignaciones(empleado) -> int:
    """Recalcula ``statusdocs`` de todas las asignaciones del empleado tras verificar/rechazar docs.

    Replica el ``checkdocs`` del origen (corregido: AND real entre todos los grupos del evento).
    Cuando una asignación transiciona de PENDIENTES → CUMPLE, notifica al empleado (correo + WA).
    Devuelve cuántas asignaciones cambiaron de estado.
    """
    from django.db import connection

    from apps.documentos.services import cumple_requisitos

    from .models import EmpleadoEventoProveedor, EventoGrupoDocumentos

    asignaciones = (
        EmpleadoEventoProveedor.objects
        .filter(empleado=empleado)
        .select_related("evento_proveedor")
    )
    nombre_tenant = connection.schema_name
    cambiadas = 0
    for asignacion in asignaciones:
        reqs = list(
            EventoGrupoDocumentos.objects
            .filter(evento_id=asignacion.evento_proveedor.evento_id)
            .values_list("grupo_id", "type_validation")
        )
        nuevo = (
            EmpleadoEventoProveedor.StatusDocs.CUMPLE
            if cumple_requisitos(empleado, reqs)
            else EmpleadoEventoProveedor.StatusDocs.PENDIENTES
        )
        if asignacion.statusdocs != nuevo:
            prev = asignacion.statusdocs
            asignacion.statusdocs = nuevo
            asignacion.save(update_fields=["statusdocs"])
            cambiadas += 1
            # Notifica al empleado cuando sus docs quedan verificados y su acceso es confirmado.
            if (prev == EmpleadoEventoProveedor.StatusDocs.PENDIENTES
                    and nuevo == EmpleadoEventoProveedor.StatusDocs.CUMPLE):
                notificar_asignacion_empleado(asignacion, nombre_tenant=nombre_tenant)
    return cambiadas


def estado_documental(empleado, requisitos) -> tuple[bool, list[dict]]:
    """Evalúa, por grupo requerido, el estado documental del empleado.

    ``requisitos`` = lista de ``EventoGrupoDocumentos`` (con ``grupo``). Devuelve
    ``(cumple_todo, detalle)`` donde detalle describe verificados/pendientes/faltantes por grupo,
    para que la UI explique por qué un empleado no es asignable todavía.
    """
    from apps.documentos.models import DocumentoEmpleado, TipoDocumento
    from apps.documentos.services import TODOS

    docs = {
        (d.tipo_documento_id, d.estado)
        for d in DocumentoEmpleado.objects.filter(empleado=empleado).only("tipo_documento_id", "estado")
    }
    verificados_ids = {tid for (tid, est) in docs if est == DocumentoEmpleado.Estado.VERIFICADO}
    pendientes_ids = {tid for (tid, est) in docs if est == DocumentoEmpleado.Estado.PENDIENTE}

    cumple_todo = True
    detalle: list[dict] = []
    for r in requisitos:
        tipos = list(TipoDocumento.objects.filter(grupo_id=r.grupo_id, activo=True).values("id", "nombre"))
        nombre = {t["id"]: t["nombre"] for t in tipos}
        ids = set(nombre)
        verif = ids & verificados_ids
        pend = ids & pendientes_ids
        if r.type_validation == TODOS:
            ok = bool(ids) and ids.issubset(verificados_ids)
            faltan = ids - verificados_ids - pendientes_ids
        else:  # al menos uno
            ok = bool(verif)
            faltan = set() if ok or pend else ids
        if not ok:
            cumple_todo = False
        detalle.append({
            "grupo": r.grupo_id,
            "grupo_nombre": r.grupo.nombre,
            "type_validation": r.type_validation,
            "ok": ok,
            "verificados": [nombre[i] for i in verif],
            "pendientes": [nombre[i] for i in pend],
            "faltantes": [nombre[i] for i in faltan],
            "tipos": tipos,
        })
    return cumple_todo, detalle


def notificar_evento_cancelado(evento, *, nombre_tenant: str) -> int:
    """Avisa a todos los proveedores invitados que el evento fue cancelado. Devuelve cuántos."""
    from .models import EventoProveedor

    invitaciones = (
        EventoProveedor.objects.filter(evento=evento).select_related("proveedor")
    )
    cuerpo_base = (
        f"El evento «{evento.nombre}» de {nombre_tenant} ha sido cancelado.\n\n"
        f"— {nombre_tenant} · Xenty Acceso"
    )
    n = 0
    for ep in invitaciones:
        _enviar_whatsapp(ep.proveedor.telefono, cuerpo_base)
        _enviar_correo(f"Evento cancelado — {evento.nombre}", cuerpo_base,
                       ep.proveedor.email_responsable or ep.proveedor.email)
        n += 1
    return n
