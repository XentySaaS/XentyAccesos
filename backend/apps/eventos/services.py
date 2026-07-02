"""Notificaciones del módulo de eventos (correo + WhatsApp), best-effort.

Replica el flujo del origen (SendNewEvent / SendWPEntry / SendWPCancelEvent / SendParking) reusando
el cliente de WhatsApp de ``apps.mensajeria`` y el correo de Django. Las notificaciones nunca
bloquean la operación: si fallan, se registran y la API responde igual (en dev, WhatsApp es sandbox
y el correo va a Mailpit).
"""
from __future__ import annotations

import logging
from datetime import datetime, time as _dtime, timezone as _dtz

from common.email_builder import construir_correo, enviar_correo_html

logger = logging.getLogger(__name__)


def _exp_epoch(evento) -> float:
    """Epoch del fin del último día de vigencia del evento (para el QR)."""
    return datetime.combine(evento.vigencia_fin, _dtime(23, 59, 59), tzinfo=_dtz.utc).timestamp()


_MESES_ES = {
    "January": "Ene", "February": "Feb", "March": "Mar", "April": "Abr",
    "May": "May", "June": "Jun", "July": "Jul", "August": "Ago",
    "September": "Sep", "October": "Oct", "November": "Nov", "December": "Dic",
}
_DIAS_ES = {
    "Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mie",
    "Thursday": "Jue", "Friday": "Vie", "Saturday": "Sab", "Sunday": "Dom",
}


def _kwargs_gafete(ep) -> dict:
    """Kwargs para componer_gafete extraídos del EventoProveedor."""
    ev = ep.evento

    def _fecha(d) -> str:
        return f"{d.day} {_MESES_ES[d.strftime('%B')]} {d.year}"

    def _hora(d, t) -> str:
        return f"{_DIAS_ES[d.strftime('%A')]} · {t.strftime('%H:%M')} hrs" if t else ""

    return dict(
        recinto=ev.recinto.nombre if ev.recinto_id else "",
        zona=ep.zona.nombre if ep.zona_id else "GENERAL",
        punto_de_acceso=ep.acceso.nombre if ep.acceso_id else "",
        nombre_evento=ev.nombre,
        fecha_evento=_fecha(ev.vigencia_inicio),
        hora_evento=_hora(ev.vigencia_inicio, ev.hora_inicio),
        vigencia_hasta=_fecha(ev.vigencia_fin),
        hora_vigencia="",
    )


def _enviar_whatsapp(telefono: str | None, cuerpo: str) -> None:
    from apps.mensajeria.services import notificar_whatsapp
    notificar_whatsapp(telefono, cuerpo)


def _enviar_correo_simple(
    asunto: str,
    cuerpo: str,
    destino: str | None,
    *,
    nombre_tenant: str = "Xenty Acceso",
    saludo: str = "",
    cta_texto: str | None = None,
    cta_url: str | None = None,
    adjuntos: list[tuple[str, bytes, str]] | None = None,
) -> None:
    """Envía correo con plantilla HTML. ``cuerpo`` se usa como texto plano y como párrafos HTML."""
    if not destino:
        return
    lineas = [l.strip() for l in cuerpo.strip().splitlines() if l.strip()]
    html = construir_correo(
        nombre_tenant=nombre_tenant,
        saludo=saludo or (lineas[0] if lineas else ""),
        parrafos=lineas[1:] if saludo else lineas,
        cta_texto=cta_texto,
        cta_url=cta_url,
        asunto=asunto,
    )
    enviar_correo_html(
        asunto=asunto,
        texto_plano=cuerpo,
        html=html,
        destino=destino,
        adjuntos=adjuntos,
    )


def notificar_invitacion(ep, *, nombre_tenant: str, panel_url: str | None = None) -> None:
    """Avisa al proveedor (correo HTML + WhatsApp) que fue invitado a un evento.

    Si tiene cajones de estacionamiento, adjunta los QR de cada cajón al correo.
    """
    from django.db import connection as _conn

    proveedor = ep.proveedor
    evento = ep.evento
    responsable = (proveedor.nombre_responsable or proveedor.nombre or "").strip().title()
    panel = (panel_url or "").rstrip("/")
    cta_url = f"{panel}/proveedores/eventos" if panel else None

    asunto = f"Invitación al evento {evento.nombre} — {nombre_tenant}"
    destino = proveedor.email_responsable or proveedor.email

    parrafos = [
        f"{nombre_tenant} te ha invitado al evento <strong>«{evento.nombre}»</strong>.",
        "Define el personal que asistirá desde la sección de <strong>Mis eventos</strong> en tu panel.",
    ]
    if ep.requiere_parking and ep.cajones_parking:
        parrafos.append(
            f"Se te asignaron <strong>{ep.cajones_parking} cajón(es) de estacionamiento</strong>"
            f"{(' (' + ep.parking + ')') if ep.parking else ''}. "
            "Los pases QR de estacionamiento van adjuntos a este correo."
        )

    texto_plano = (
        f"Hola {responsable},\n\n"
        + "\n\n".join(p.replace("<strong>", "").replace("</strong>", "") for p in parrafos)
        + (f"\n\nIngresa aquí: {cta_url}" if cta_url else "")
        + f"\n\n— {nombre_tenant} · Xenty Acceso"
    )

    # Adjuntar QR de estacionamiento si hay cajones
    adjuntos: list[tuple[str, bytes, str]] = []
    if ep.requiere_parking:
        try:
            from apps.gafetes.services import TIPO_PARKING, componer_gafete_estacionamiento, emitir_qr
            exp     = _exp_epoch(evento)
            fecha_v = evento.vigencia_inicio.strftime("%d/%m/%Y")
            recinto = evento.recinto.nombre if evento.recinto_id else nombre_tenant
            for i, cajon in enumerate(ep.cajones.order_by("id"), start=1):
                token = emitir_qr(
                    id=cajon.id, tipo=TIPO_PARKING, tenant=_conn.schema_name,
                    exp_epoch=exp, contexto=str(cajon.uuid),
                )
                png = componer_gafete_estacionamiento(
                    token=token,
                    nombre_empresa=proveedor.nombre,
                    recinto=recinto,
                    evento=evento.nombre,
                    parking=ep.parking or "",
                    cajon=f"C-{i}",
                    vigencia=fecha_v,
                    empresa=nombre_tenant,
                )
                adjuntos.append((f"pase-estacionamiento-{i}.png", png, "image/png"))
        except Exception as exc:
            logger.warning("QR parking no generado para invitación %s: %s", ep.id, exc)

    html = construir_correo(
        nombre_tenant=nombre_tenant,
        saludo=f"Hola {responsable},",
        parrafos=parrafos,
        cta_texto="Ingresar al panel de proveedor" if cta_url else None,
        cta_url=cta_url,
        asunto=asunto,
    )
    enviar_correo_html(
        asunto=asunto, texto_plano=texto_plano, html=html,
        destino=destino, adjuntos=adjuntos or None,
    )
    _enviar_whatsapp(proveedor.telefono, texto_plano)


def notificar_invitacion_cancelada(ep, *, nombre_tenant: str) -> None:
    """Avisa al proveedor que su invitación a un evento fue retirada."""
    proveedor = ep.proveedor
    asunto = f"Invitación cancelada — {ep.evento.nombre}"
    destino = proveedor.email_responsable or proveedor.email
    parrafos = [
        f"Tu invitación al evento <strong>«{ep.evento.nombre}»</strong> "
        f"de {nombre_tenant} ha sido cancelada.",
        "Si tienes dudas, comunícate directamente con el organizador del evento.",
    ]
    texto_plano = (
        f"Tu invitación al evento «{ep.evento.nombre}» de {nombre_tenant} ha sido cancelada.\n\n"
        f"— {nombre_tenant} · Xenty Acceso"
    )
    html = construir_correo(
        nombre_tenant=nombre_tenant,
        saludo="Aviso importante,",
        parrafos=parrafos,
        asunto=asunto,
    )
    _enviar_whatsapp(proveedor.telefono, texto_plano)
    enviar_correo_html(asunto=asunto, texto_plano=texto_plano, html=html, destino=destino)


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
    """Avisa al empleado (correo HTML + WhatsApp) que fue asignado a un evento.

    Adjunta el gafete QR como PNG al correo para que el empleado lo presente en el acceso.
    """
    from django.db import connection as _conn

    empleado = asignacion.empleado
    ep = asignacion.evento_proveedor
    ev = ep.evento
    asunto = f"Tu gafete de acceso — {ev.nombre}"
    resumen = _resumen_evento(ep)

    parrafos = [
        f"{nombre_tenant} te ha asignado al evento {resumen}.",
        "Tu <strong>gafete de acceso QR</strong> va adjunto a este correo. "
        "Preséntalo en el punto de acceso indicado al llegar al recinto.",
    ]
    texto_plano = (
        f"Hola {empleado.nombre},\n\n"
        f"{nombre_tenant} te asignó al evento {resumen}.\n\n"
        "Tu gafete de acceso QR va adjunto a este correo. "
        "Preséntalo en el punto de acceso indicado."
    )

    # Genera el gafete (best-effort)
    adjunto: list[tuple[str, bytes, str]] | None = None
    try:
        from apps.gafetes.services import TIPO_EVENTO, componer_gafete, emitir_qr

        token = emitir_qr(
            id=asignacion.id, tipo=TIPO_EVENTO,
            tenant=_conn.schema_name, exp_epoch=_exp_epoch(ev),
        )
        foto: bytes | None = None
        if empleado.foto:
            try:
                foto = empleado.foto.read()
            except OSError:
                pass
        recinto = ev.recinto.nombre if ev.recinto_id else nombre_tenant
        png = componer_gafete(
            token=token,
            nombre_invitado=empleado.nombre,
            foto_bytes=foto,
            empresa=nombre_tenant,
            **_kwargs_gafete(ep),
        )
        nombre_f = f"gafete-{empleado.nombre.replace(' ', '-').lower()}.png"
        adjunto = [(nombre_f, png, "image/png")]
    except Exception as exc:
        logger.warning("Gafete no generado/adjuntado para asignación %s: %s", asignacion.id, exc)

    html = construir_correo(
        nombre_tenant=nombre_tenant,
        saludo=f"Hola {empleado.nombre},",
        parrafos=parrafos,
        asunto=asunto,
    )
    enviar_correo_html(
        asunto=asunto, texto_plano=texto_plano, html=html,
        destino=empleado.email, adjuntos=adjunto,
    )
    _enviar_whatsapp(empleado.telefono, texto_plano)


def notificar_desasignacion_empleado(empleado, evento, *, nombre_tenant: str) -> None:
    """Avisa al empleado que su acceso al evento fue revocado."""
    asunto = f"Acceso revocado — {evento.nombre}"
    parrafos = [
        f"Tu acceso al evento <strong>«{evento.nombre}»</strong> de {nombre_tenant} "
        "ha sido revocado.",
        "Si crees que esto es un error, comunícate con el responsable de tu empresa.",
    ]
    texto_plano = (
        f"Hola {empleado.nombre}, tu acceso al evento «{evento.nombre}» de {nombre_tenant} "
        "ha sido revocado."
    )
    html = construir_correo(
        nombre_tenant=nombre_tenant,
        saludo=f"Hola {empleado.nombre},",
        parrafos=parrafos,
        asunto=asunto,
    )
    enviar_correo_html(asunto=asunto, texto_plano=texto_plano, html=html, destino=empleado.email)
    _enviar_whatsapp(empleado.telefono, texto_plano)


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

    asunto = f"Evento cancelado — {evento.nombre}"
    parrafos = [
        f"El evento <strong>«{evento.nombre}»</strong> de {nombre_tenant} ha sido cancelado.",
        "Si tienes dudas sobre esta decisión, comunícate directamente con el organizador.",
    ]
    texto_plano = (
        f"El evento «{evento.nombre}» de {nombre_tenant} ha sido cancelado.\n\n"
        f"— {nombre_tenant} · Xenty Acceso"
    )
    invitaciones = (
        EventoProveedor.objects.filter(evento=evento).select_related("proveedor")
    )
    n = 0
    for ep in invitaciones:
        responsable = (ep.proveedor.nombre_responsable or ep.proveedor.nombre or "").strip().title()
        html = construir_correo(
            nombre_tenant=nombre_tenant,
            saludo=f"Hola {responsable}," if responsable else "Estimado proveedor,",
            parrafos=parrafos,
            asunto=asunto,
        )
        _enviar_whatsapp(ep.proveedor.telefono, texto_plano)
        enviar_correo_html(
            asunto=asunto, texto_plano=texto_plano, html=html,
            destino=ep.proveedor.email_responsable or ep.proveedor.email,
        )
        n += 1
    return n
