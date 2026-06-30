"""Servicios de citas: notificaciones al crear una cita.

Envía correo HTML al responsable del proveedor (cita tipo 0) o a cada
asistente con email (cita tipo 1). Best-effort: los errores se loguean
sin propagar para no bloquear la respuesta HTTP.
"""
from __future__ import annotations

import logging

from common.email_builder import construir_correo, enviar_correo_html

logger = logging.getLogger(__name__)


def enviar_notificacion_cita(cita) -> int:
    """Envía la notificación y devuelve el número de correos intentados."""
    try:
        logger.info(
            "enviar_notificacion_cita pk=%s tipo=%s tipo_cita=%s",
            cita.pk, cita.tipo, cita.tipo_cita,
        )
        # Walk-in: el acceso se registra automáticamente, no se envían invitaciones por correo.
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


def _fmt_fecha(cita) -> str:
    return cita.fecha.strftime("%d/%m/%Y") if cita.fecha else "—"


def _fmt_hora(cita) -> str:
    return cita.hora_inicio.strftime("%H:%M") if cita.hora_inicio else "—"


def _nombre_tenant(cita) -> str:
    try:
        from django_tenants.utils import get_tenant
        t = get_tenant(None)
        return getattr(t, "company", None) or getattr(t, "nombre", "Xenty Accesos")
    except Exception:  # noqa: BLE001
        return "Xenty Accesos"


def _notificar_asistentes(cita) -> int:
    import datetime
    from django.db import connection

    tenant = _nombre_tenant(cita)
    fecha = _fmt_fecha(cita)
    hora = _fmt_hora(cita)
    recinto = cita.recinto.nombre if cita.recinto else ""
    zona = cita.ubicacion.nombre if cita.ubicacion else "GENERAL"
    punto = cita.punto_acceso.nombre if cita.punto_acceso else ""

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

    schema = connection.schema_name
    enviados = 0
    total = cita.asistentes.count()
    logger.info("_notificar_asistentes cita pk=%s total_asistentes=%s", cita.pk, total)

    for asistente in cita.asistentes.all():
        if not asistente.email:
            logger.info("Asistente pk=%s sin email — omitido", asistente.pk)
            continue

        # Intentar adjuntar gafete QR; si falla (Pillow/qrcode no instalado, etc.)
        # el correo se envía igual, sin adjunto.
        adjuntos = None
        try:
            from apps.gafetes.services import TIPO_CITA, componer_gafete, emitir_qr
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
                nombre_evento=cita.nombre or "Cita",
                fecha_evento=fecha,
                hora_evento=hora,
                vigencia_hasta=vigencia_hasta,
                hora_vigencia=hora_vigencia,
                label_zona="ÁREA",
                label_evento="NOMBRE DE LA CITA",
                label_fecha="FECHA DE LA CITA",
            )
            adjuntos = [(f"gafete_cita_{cita.pk}_{asistente.pk}.png", gafete_bytes, "image/png")]
        except Exception:  # noqa: BLE001
            logger.warning("Gafete no generado para asistente pk=%s — se envía sin adjunto", asistente.pk)

        con_gafete = adjuntos is not None
        logger.info(
            "Enviando correo a %s (asistente pk=%s) con_gafete=%s",
            asistente.email, asistente.pk, con_gafete,
        )
        html = construir_correo(
            nombre_tenant=tenant,
            asunto=f"Invitación: {cita.nombre or 'cita'}",
            saludo=f"Hola {asistente.nombre},",
            parrafos=[
                f"Has sido invitado a <strong>{cita.nombre or 'una cita'}</strong>.",
                f"Fecha: {fecha} &nbsp;·&nbsp; Hora: {hora}",
                f"Recinto: {recinto}",
                "Presenta el <strong>gafete adjunto</strong> al llegar para registrar tu acceso."
                if con_gafete else
                "Presenta este correo al llegar para registrar tu acceso.",
            ],
        )
        enviar_correo_html(
            asunto=f"Invitación: {cita.nombre or 'cita'}",
            texto_plano=(
                f"Invitado a {cita.nombre} el {fecha} a las {hora}. "
                f"Recinto: {recinto}. "
                + ("Presenta el gafete adjunto al llegar." if con_gafete else "Presenta este correo al llegar.")
            ),
            html=html,
            destino=asistente.email,
            adjuntos=adjuntos,
        )
        enviados += 1

    logger.info("_notificar_asistentes cita pk=%s enviados=%s", cita.pk, enviados)
    return enviados


def _notificar_proveedor(cita) -> None:
    if not cita.proveedor:
        return
    p = cita.proveedor
    email = getattr(p, "email_responsable", None) or getattr(p, "email", None)
    if not email:
        return

    tenant = _nombre_tenant(cita)
    fecha = _fmt_fecha(cita)
    hora = _fmt_hora(cita)
    recinto = cita.recinto.nombre if cita.recinto else "—"
    nombre_resp = getattr(p, "nombre_responsable", None) or p.nombre or "Responsable"

    html = construir_correo(
        nombre_tenant=tenant,
        asunto=f"Nueva cita: {cita.nombre or 'cita'}",
        saludo=f"Hola {nombre_resp},",
        parrafos=[
            f"Se ha programado la cita <strong>{cita.nombre or 'Cita'}</strong>.",
            f"Fecha: {fecha} &nbsp;·&nbsp; Hora: {hora}",
            f"Recinto: {recinto}",
            f"Personas invitadas: {cita.limite or '—'}",
            "Ingresa al panel de proveedores para asignar el personal que asistirá.",
        ],
    )
    enviar_correo_html(
        asunto=f"Nueva cita: {cita.nombre or 'cita'}",
        texto_plano=f"Cita {cita.nombre} el {fecha} a las {hora}. Recinto: {recinto}.",
        html=html,
        destino=email,
    )
