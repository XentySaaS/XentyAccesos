"""Servicios de citas: notificaciones al crear una cita.

Envía correo HTML al responsable del proveedor (cita tipo 0) o a cada
asistente con email (cita tipo 1). Best-effort: los errores se loguean
sin propagar para no bloquear la respuesta HTTP.
"""
from __future__ import annotations

import logging

from common.email_builder import construir_correo, enviar_correo_html

logger = logging.getLogger(__name__)


def enviar_notificacion_cita(cita) -> None:
    try:
        if cita.tipo == 1:
            _notificar_asistentes(cita)
        else:
            _notificar_proveedor(cita)
    except Exception:  # noqa: BLE001
        logger.exception("Error enviando notificación de cita pk=%s", cita.pk)


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


def _notificar_asistentes(cita) -> None:
    tenant = _nombre_tenant(cita)
    fecha = _fmt_fecha(cita)
    hora = _fmt_hora(cita)
    recinto = cita.recinto.nombre if cita.recinto else "—"

    for asistente in cita.asistentes.all():
        if not asistente.email:
            continue
        html = construir_correo(
            nombre_tenant=tenant,
            asunto=f"Invitación: {cita.nombre or 'cita'}",
            saludo=f"Hola {asistente.nombre},",
            parrafos=[
                f"Has sido invitado a <strong>{cita.nombre or 'una cita'}</strong>.",
                f"Fecha: {fecha} &nbsp;·&nbsp; Hora: {hora}",
                f"Recinto: {recinto}",
            ],
        )
        enviar_correo_html(
            asunto=f"Invitación: {cita.nombre or 'cita'}",
            texto_plano=f"Invitado a {cita.nombre} el {fecha} a las {hora}. Recinto: {recinto}.",
            html=html,
            destino=asistente.email,
        )


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
