"""Servicios de citas: notificaciones de invitación y de cancelación.

Al crear/actualizar una cita se envía la invitación (correo HTML + WhatsApp) con el **gafete QR** y el
**protocolo de acceso** adjuntos por ambos canales. Al cancelar, se envía un aviso de cancelación
claro (sin gafete). Todo es best-effort: los errores se loguean sin propagar para no bloquear la
respuesta HTTP.
"""

from __future__ import annotations

import logging

from common.email_builder import construir_correo, enviar_correo_html

logger = logging.getLogger(__name__)


def enviar_notificacion_cita(cita) -> int:
    """Envía la invitación y devuelve el número de destinatarios intentados."""
    try:
        logger.info(
            "enviar_notificacion_cita pk=%s tipo=%s tipo_cita=%s",
            cita.pk,
            cita.tipo,
            cita.tipo_cita,
        )
        # Walk-in: el acceso se registra automáticamente, no se envían invitaciones.
        if cita.tipo_cita == "walk_in":
            logger.info("Cita pk=%s es walk_in — sin notificación", cita.pk)
            return 0
        if cita.tipo == 1:
            return _notificar_asistentes(cita)
        else:
            _notificar_proveedor(cita)
            return 1
    except Exception:  # noqa: BLE001
        logger.exception("Error enviando notificación de cita pk=%s", cita.pk)
        return 0


def enviar_cancelacion_cita(cita) -> int:
    """Avisa a los invitados que la cita fue **cancelada** (correo + WhatsApp, sin gafete)."""
    try:
        if cita.tipo_cita == "walk_in":
            return 0
        if cita.tipo == 1:
            return _cancelar_asistentes(cita)
        else:
            _cancelar_proveedor(cita)
            return 1
    except Exception:  # noqa: BLE001
        logger.exception("Error enviando cancelación de cita pk=%s", cita.pk)
        return 0


def enviar_invitacion_asistentes(cita, asistentes) -> int:
    """Envía la invitación (gafete + protocolo) solo a un subconjunto de asistentes.

    Se usa al **agregar** invitados a una cita existente: se invita únicamente a los nuevos, sin
    reenviar a los que ya la habían recibido. Best-effort.
    """
    try:
        if cita.tipo_cita == "walk_in":
            return 0
        return _notificar_asistentes(cita, asistentes=list(asistentes))
    except Exception:  # noqa: BLE001
        logger.exception("Error invitando asistentes de cita pk=%s", cita.pk)
        return 0


def enviar_baja_asistente(cita, asistente) -> bool:
    """Avisa a UN asistente que fue **dado de baja** de la cita (correo + WhatsApp, sin gafete)."""
    try:
        if cita.tipo_cita == "walk_in" or (not asistente.email and not asistente.telefono):
            return False
        from apps.mensajeria.services import notificar_whatsapp

        ctx = _contexto(cita)
        texto_plano = (
            f"Hola {asistente.nombre}:\n\n"
            f"Fue dado de baja de la cita «{ctx['nombre']}».\n\n"
            f"{_detalle_texto(ctx)}\n\n"
            "El gafete o invitación que haya recibido queda sin validez.\n"
            f"\n— {ctx['tenant']}"
        )
        html = construir_correo(
            nombre_tenant=ctx["tenant"],
            tipo="modificacion",
            titulo="Fuiste dado de baja de la cita",
            subtitulo=f"Ya no formas parte de «{ctx['nombre']}».",
            filas=_filas_cita(ctx, {"label": "Invitado", "valor": asistente.nombre}),
            card_titulo="Cita",
            mensaje=(
                "El gafete o invitación que haya recibido para esta cita <strong>queda sin "
                "validez</strong>. Si tiene dudas, comuníquese con el organizador."
            ),
            asunto=f"Baja de cita: {ctx['nombre']}",
            pre_header=f"Fuiste dado de baja de «{ctx['nombre']}».",
        )
        if asistente.email:
            enviar_correo_html(
                asunto=f"Baja de cita: {ctx['nombre']}",
                texto_plano=texto_plano,
                html=html,
                destino=asistente.email,
            )
        notificar_whatsapp(asistente.telefono, texto_plano)
        return True
    except Exception:  # noqa: BLE001
        logger.exception(
            "Error notificando baja de asistente pk=%s", getattr(asistente, "pk", None)
        )
        return False


# ── Helpers de formato / contexto ─────────────────────────────────────────────


def _fmt_fecha(cita) -> str:
    return cita.fecha.strftime("%d/%m/%Y") if cita.fecha else "por confirmar"


def _fmt_hora(cita) -> str:
    return cita.hora_inicio.strftime("%H:%M hrs") if cita.hora_inicio else "por confirmar"


def _nombre_tenant(cita) -> str:
    """Nombre display del tenant (quien invita); p. ej. «3 Museos», no el schema «museos»."""
    from common.tenant import nombre_tenant_actual

    return nombre_tenant_actual()


def _contexto(cita) -> dict:
    """Datos legibles de la cita, reutilizados por invitación y cancelación."""
    return {
        "tenant": _nombre_tenant(cita),
        "nombre": cita.nombre or "Cita",
        "fecha": _fmt_fecha(cita),
        "hora": _fmt_hora(cita),
        "recinto": cita.recinto.nombre if cita.recinto else "",
        "zona": cita.ubicacion.nombre if cita.ubicacion else "",
        "punto": cita.punto_acceso.nombre if cita.punto_acceso else "",
        "protocolo": cita.protocolo.nombre if cita.protocolo_id else "",
    }


def _detalle_texto(ctx: dict) -> str:
    """Bloque de detalles para WhatsApp (texto plano con íconos)."""
    partes = [
        f"📅 Fecha: {ctx['fecha']}",
        f"🕐 Hora: {ctx['hora']}",
    ]
    if ctx["recinto"]:
        partes.append(f"📍 Recinto: {ctx['recinto']}")
    if ctx["zona"]:
        partes.append(f"🏷️ Área: {ctx['zona']}")
    if ctx["punto"]:
        partes.append(f"🚪 Punto de acceso: {ctx['punto']}")
    if ctx["protocolo"]:
        partes.append(f"📋 Protocolo: {ctx['protocolo']}")
    return "\n".join(partes)


def _filas_cita(ctx: dict, primero: dict) -> list[dict]:
    """Celdas de la tarjeta del correo (``primero`` = Invitado o Responsable)."""
    filas = [
        primero,
        {"label": "Cita", "valor": ctx["nombre"]},
        {"label": "Fecha", "valor": ctx["fecha"]},
        {"label": "Hora", "valor": ctx["hora"]},
    ]
    if ctx["recinto"]:
        filas.append({"label": "Recinto", "valor": ctx["recinto"]})
    if ctx["zona"]:
        filas.append({"label": "Área", "valor": ctx["zona"]})
    if ctx["punto"]:
        filas.append({"label": "Punto de acceso", "valor": ctx["punto"]})
    if ctx["protocolo"]:
        filas.append({"label": "Protocolo", "valor": ctx["protocolo"]})
    return filas


# ── Invitación ────────────────────────────────────────────────────────────────


def _notificar_asistentes(cita, asistentes=None) -> int:
    import datetime

    from django.db import connection

    from apps.mensajeria.proveedores import AdjuntoWhatsApp
    from apps.mensajeria.services import adjunto_protocolo, notificar_whatsapp

    from .models import AsistenteCita

    # None = todos los activos (los cancelados no se re-invitan); una lista = solo esos (recién agregados).
    lista = (
        list(asistentes)
        if asistentes is not None
        else list(cita.asistentes.exclude(estado=AsistenteCita.Estado.CANCELADO))
    )

    ctx = _contexto(cita)
    fecha, hora, recinto = ctx["fecha"], ctx["hora"], ctx["recinto"]
    zona = ctx["zona"] or "GENERAL"
    punto = ctx["punto"]

    if cita.fecha:
        exp_epoch = datetime.datetime.combine(
            cita.fecha + datetime.timedelta(days=1), datetime.time.min
        ).timestamp()
        vigencia_hasta = cita.fecha.strftime("%d/%m/%Y")
        hora_vigencia = "23:59"
    else:
        exp_epoch = (datetime.datetime.now() + datetime.timedelta(days=7)).timestamp()
        vigencia_hasta = ""
        hora_vigencia = ""

    # Protocolo: se lee una sola vez y se reutiliza para todos los asistentes (mismo PDF).
    prot_adj = (
        adjunto_protocolo(
            cita.protocolo,
            caption=f"📋 Protocolo de acceso: {ctx['protocolo']}. Consúltalo antes de tu visita.",
        )
        if cita.protocolo_id
        else None
    )

    schema = connection.schema_name
    enviados = 0
    logger.info("_notificar_asistentes cita pk=%s total_asistentes=%s", cita.pk, len(lista))

    for asistente in lista:
        if not asistente.email and not asistente.telefono:
            logger.info("Asistente pk=%s sin email ni teléfono — omitido", asistente.pk)
            continue

        # Genera el gafete QR (best-effort: si falla, se avisa igual sin adjunto).
        gafete_adj: AdjuntoWhatsApp | None = None
        try:
            from apps.gafetes.services import TIPO_CITA, componer_gafete, emitir_qr

            foto_bytes: bytes | None = None
            if asistente.tipo == asistente.Tipo.EMPLEADO and asistente.persona is not None:
                try:
                    emp = asistente.persona
                    if getattr(emp, "foto", None) and emp.foto.name:
                        foto_bytes = emp.foto.read()
                except Exception:  # noqa: BLE001
                    foto_bytes = None

            token = emitir_qr(
                id=asistente.id,
                tipo=TIPO_CITA,
                tenant=schema,
                exp_epoch=exp_epoch,
                contexto=f"cita:{cita.pk}",
            )
            gafete_bytes = componer_gafete(
                token=token,
                nombre_invitado=asistente.nombre,
                recinto=recinto,
                zona=zona,
                punto_de_acceso=punto,
                nombre_evento=ctx["nombre"],
                fecha_evento=fecha,
                hora_evento=hora,
                vigencia_hasta=vigencia_hasta,
                hora_vigencia=hora_vigencia,
                foto_bytes=foto_bytes,
                label_zona="ÁREA",
                label_evento="NOMBRE DE LA CITA",
                label_fecha="FECHA DE LA CITA",
            )
            gafete_adj = AdjuntoWhatsApp(
                nombre_archivo=f"gafete_cita_{cita.pk}_{asistente.pk}.png",
                contenido=gafete_bytes,
                mimetype="image/png",
                caption=f"🎫 Tu gafete de acceso para «{ctx['nombre']}». Preséntalo en el punto de acceso.",
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "Gafete no generado para asistente pk=%s — se notifica sin adjunto", asistente.pk
            )

        con_gafete = gafete_adj is not None
        con_protocolo = prot_adj is not None
        requiere_ine = bool(getattr(asistente, "requiere_ine", False))

        # ── Correo (tarjeta de acceso + adjuntos: gafete y protocolo) ──
        instrucciones = [
            "Presente el <strong>gafete adjunto</strong> (código QR) en el punto de acceso "
            "para registrar su ingreso."
            if con_gafete
            else "Presente este correo en el punto de acceso para registrar su ingreso."
        ]
        if requiere_ine:
            instrucciones.append(
                "Traiga una <strong>identificación oficial vigente</strong> (INE)."
            )
        if con_protocolo:
            instrucciones.append(
                f"Adjuntamos el <strong>protocolo de acceso</strong> («{ctx['protocolo']}»); "
                "le pedimos revisarlo antes de su visita."
            )
        instrucciones.append(
            f"Su acceso es personal e intransferible y estará vigente hasta el {vigencia_hasta}."
            if vigencia_hasta
            else "Su acceso es personal e intransferible."
        )

        adjuntos_correo: list[tuple[str, bytes, str]] = []
        if gafete_adj:
            adjuntos_correo.append(
                (gafete_adj.nombre_archivo, gafete_adj.contenido, gafete_adj.mimetype)
            )
        if prot_adj:
            adjuntos_correo.append((prot_adj.nombre_archivo, prot_adj.contenido, prot_adj.mimetype))

        html = construir_correo(
            nombre_tenant=ctx["tenant"],
            tipo="acceso",
            titulo="Tu acceso está confirmado",
            subtitulo=f"{ctx['tenant']} te registró como invitado a «{ctx['nombre']}».",
            filas=_filas_cita(ctx, {"label": "Invitado", "valor": asistente.nombre}),
            card_titulo="Detalles del acceso",
            mensaje=" ".join(instrucciones),
            asunto=f"Invitación: {ctx['nombre']}",
            pre_header=f"Tu acceso a «{ctx['nombre']}» está listo.",
            footer_legal="El acceso es personal e intransferible y válido únicamente para el titular registrado. Xenty Accesos.",
        )

        # ── WhatsApp (texto profesional + gafete y protocolo como media) ──
        texto_plano = (
            f"Hola {asistente.nombre}:\n\n"
            f"{ctx['tenant']} le invita a «{ctx['nombre']}».\n\n"
            f"{_detalle_texto(ctx)}\n\n"
            + (
                "Le enviamos su gafete de acceso (QR); preséntelo en el punto de acceso.\n"
                if con_gafete
                else "Presente esta invitación en el punto de acceso.\n"
            )
            + ("Traiga identificación oficial vigente (INE).\n" if requiere_ine else "")
            + (
                f"\nSu acceso es personal e intransferible; vigente hasta el {vigencia_hasta}."
                if vigencia_hasta
                else "\nSu acceso es personal e intransferible."
            )
            + f"\n\n— {ctx['tenant']}"
        )

        con_correo = bool(asistente.email)
        logger.info(
            "Notificando asistente pk=%s correo=%s con_gafete=%s con_protocolo=%s",
            asistente.pk,
            con_correo,
            con_gafete,
            con_protocolo,
        )
        if con_correo:
            enviar_correo_html(
                asunto=f"Invitación: {ctx['nombre']}",
                texto_plano=texto_plano,
                html=html,
                destino=asistente.email,
                adjuntos=adjuntos_correo or None,
            )
        wa_adjuntos = [a for a in (gafete_adj, prot_adj) if a is not None]
        notificar_whatsapp(asistente.telefono, texto_plano, adjuntos=wa_adjuntos)
        enviados += 1

    logger.info("_notificar_asistentes cita pk=%s enviados=%s", cita.pk, enviados)
    return enviados


def _notificar_proveedor(cita) -> None:
    if not cita.proveedor:
        return
    p = cita.proveedor
    email = getattr(p, "email_responsable", None) or getattr(p, "email", None)
    telefono = getattr(p, "telefono", None)
    if not email and not telefono:
        return

    from apps.mensajeria.services import adjunto_protocolo, notificar_whatsapp

    ctx = _contexto(cita)
    nombre_resp = getattr(p, "nombre_responsable", None) or p.nombre or "Responsable"
    prot_adj = (
        adjunto_protocolo(
            cita.protocolo,
            caption=f"📋 Protocolo de acceso: {ctx['protocolo']}. Compártelo con tu personal.",
        )
        if cita.protocolo_id
        else None
    )

    filas = _filas_cita(ctx, {"label": "Responsable", "valor": nombre_resp})
    if cita.limite:
        filas.append({"label": "Personas permitidas", "valor": str(cita.limite)})
    mensaje = (
        "Ingrese al panel de proveedores para asignar al personal que asistirá; cada persona "
        "recibirá su gafete de acceso con código QR."
    )
    if prot_adj:
        mensaje += (
            f" Adjuntamos el <strong>protocolo de acceso</strong> («{ctx['protocolo']}»); "
            "compártalo con el personal asignado."
        )

    texto_plano = (
        f"Hola {nombre_resp}:\n\n"
        f"{ctx['tenant']} programó la cita «{ctx['nombre']}» para su empresa.\n\n"
        f"{_detalle_texto(ctx)}\n"
        + (f"👥 Personas permitidas: {cita.limite}\n" if cita.limite else "")
        + "\nAsigne a su personal desde el panel de proveedores; cada persona recibirá su gafete "
        "de acceso.\n"
        f"\n— {ctx['tenant']}"
    )

    html = construir_correo(
        nombre_tenant=ctx["tenant"],
        tipo="acceso",
        titulo="Nueva cita programada",
        subtitulo=f"{ctx['tenant']} programó «{ctx['nombre']}» para tu empresa.",
        filas=filas,
        card_titulo="Detalles de la cita",
        mensaje=mensaje,
        asunto=f"Nueva cita: {ctx['nombre']}",
        pre_header=f"Nueva cita para tu empresa: «{ctx['nombre']}».",
    )
    if email:
        enviar_correo_html(
            asunto=f"Nueva cita: {ctx['nombre']}",
            texto_plano=texto_plano,
            html=html,
            destino=email,
            adjuntos=[(prot_adj.nombre_archivo, prot_adj.contenido, prot_adj.mimetype)]
            if prot_adj
            else None,
        )
    notificar_whatsapp(telefono, texto_plano, adjuntos=[prot_adj] if prot_adj else None)


# ── Cancelación ───────────────────────────────────────────────────────────────


def _cancelar_asistentes(cita) -> int:
    from apps.mensajeria.services import notificar_whatsapp

    ctx = _contexto(cita)
    enviados = 0
    for asistente in cita.asistentes.all():
        if not asistente.email and not asistente.telefono:
            continue
        texto_plano = (
            f"Hola {asistente.nombre}:\n\n"
            f"La cita «{ctx['nombre']}» a la que estaba invitado ha sido CANCELADA.\n\n"
            f"{_detalle_texto(ctx)}\n\n"
            "El gafete o invitación que haya recibido queda sin validez. "
            "Si se reprograma, recibirá una nueva invitación.\n"
            f"\n— {ctx['tenant']}"
        )
        html = construir_correo(
            nombre_tenant=ctx["tenant"],
            tipo="modificacion",
            titulo="Cita cancelada",
            subtitulo=f"La cita «{ctx['nombre']}» a la que estabas invitado fue cancelada.",
            filas=_filas_cita(ctx, {"label": "Invitado", "valor": asistente.nombre}),
            card_titulo="Cita cancelada",
            mensaje=(
                "El gafete o invitación que haya recibido para esta cita <strong>queda sin "
                "validez</strong>. Si se reprograma, recibirá una nueva invitación. Si tiene dudas, "
                "comuníquese con el organizador."
            ),
            asunto=f"Cita cancelada: {ctx['nombre']}",
            pre_header=f"La cita «{ctx['nombre']}» fue cancelada.",
        )
        if asistente.email:
            enviar_correo_html(
                asunto=f"Cita cancelada: {ctx['nombre']}",
                texto_plano=texto_plano,
                html=html,
                destino=asistente.email,
            )
        notificar_whatsapp(asistente.telefono, texto_plano)
        enviados += 1
    return enviados


def _cancelar_proveedor(cita) -> None:
    if not cita.proveedor:
        return
    p = cita.proveedor
    email = getattr(p, "email_responsable", None) or getattr(p, "email", None)
    telefono = getattr(p, "telefono", None)
    if not email and not telefono:
        return

    from apps.mensajeria.services import notificar_whatsapp

    ctx = _contexto(cita)
    nombre_resp = getattr(p, "nombre_responsable", None) or p.nombre or "Responsable"
    texto_plano = (
        f"Hola {nombre_resp}:\n\n"
        f"La cita «{ctx['nombre']}» programada para su empresa ha sido CANCELADA.\n\n"
        f"{_detalle_texto(ctx)}\n\n"
        "Los gafetes emitidos quedan sin validez. Si se reprograma, se le notificará.\n"
        f"\n— {ctx['tenant']}"
    )
    html = construir_correo(
        nombre_tenant=ctx["tenant"],
        tipo="modificacion",
        titulo="Cita cancelada",
        subtitulo=f"La cita «{ctx['nombre']}» programada para tu empresa fue cancelada.",
        filas=_filas_cita(ctx, {"label": "Responsable", "valor": nombre_resp}),
        card_titulo="Cita cancelada",
        mensaje=(
            "Los gafetes emitidos para esta cita <strong>quedan sin validez</strong>. Si se "
            "reprograma, se le notificará nuevamente. Si tiene dudas, comuníquese con el organizador."
        ),
        asunto=f"Cita cancelada: {ctx['nombre']}",
        pre_header=f"La cita «{ctx['nombre']}» fue cancelada.",
    )
    if email:
        enviar_correo_html(
            asunto=f"Cita cancelada: {ctx['nombre']}",
            texto_plano=texto_plano,
            html=html,
            destino=email,
        )
    notificar_whatsapp(telefono, texto_plano)
