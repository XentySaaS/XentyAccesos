"""Contexto enriquecido del escaneo (paridad con el original): datos del evento/cita, documentos
del empleado e historial de accesos, para que el guardia coteje.

Todo es *best-effort*: cada bloque va en try/except para no tumbar nunca el veredicto del escaneo
(que es lo crítico). Devuelve estructuras JSON-serializables por DRF.
"""
from __future__ import annotations

from .models import RegistroAcceso, RegistroAccesoParking


def _nombre(obj) -> str:
    return getattr(obj, "nombre", None) or "—" if obj else "—"


def _horario(hi, hf) -> str:
    if not hi and not hf:
        return "—"
    fmt = lambda t: t.strftime("%H:%M") if t else "—"  # noqa: E731
    return f"{fmt(hi)} – {fmt(hf)}"


def _contacto(reg) -> dict:
    if getattr(reg, "empleado_id", None):
        e = reg.empleado
        return {"email": e.email, "telefono": e.telefono}
    if getattr(reg, "asistente_id", None):
        a = reg.asistente
        return {"email": a.email, "telefono": a.telefono}
    return {"email": None, "telefono": None}


def _historial(reg) -> list[dict]:
    """Últimos 8 accesos de la misma persona (o cajón, en parking)."""
    if isinstance(reg, RegistroAccesoParking):
        qs = RegistroAccesoParking.objects.filter(cajon_id=reg.cajon_id)
    elif getattr(reg, "empleado_id", None):
        qs = RegistroAcceso.objects.filter(empleado_id=reg.empleado_id)
    elif getattr(reg, "asistente_id", None):
        qs = RegistroAcceso.objects.filter(asistente_id=reg.asistente_id)
    else:
        return []
    return [
        {
            "tipo_acceso": r.tipo_acceso,
            "hora_entrada": r.hora_entrada,
            "hora_salida": getattr(r, "hora_salida", None),
        }
        for r in qs.order_by("-hora_entrada")[:8]
    ]


def _detalle_evento(request, reg) -> tuple[dict, list]:
    from apps.documentos.models import DocumentoEmpleado, TipoDocumento
    from apps.eventos.models import (
        EmpleadoEventoProveedor,
        EventoGrupoDocumentos,
        EventoTipoDocumento,
    )

    ev = reg.evento
    campos = [
        {"label": "Recinto", "valor": _nombre(ev.recinto)},
        {"label": "Evento", "valor": ev.nombre},
        {"label": "Vigencia", "valor": f"{ev.vigencia_inicio} — {ev.vigencia_fin}"},
        {"label": "Horario", "valor": _horario(ev.hora_inicio, ev.hora_fin)},
        {"label": "Protocolo", "valor": _nombre(ev.protocolo)},
        {"label": "Descripción", "valor": ev.descripcion or "—"},
    ]
    eep = (
        EmpleadoEventoProveedor.objects
        .select_related("evento_proveedor__zona", "evento_proveedor__punto_acceso")
        .filter(empleado_id=reg.empleado_id, evento_proveedor__evento_id=ev.id)
        .first()
    )
    if eep:
        ep = eep.evento_proveedor
        areas = ", ".join(a.nombre for a in ep.areas_autorizadas.all()) or "—"
        campos += [
            {"label": "Zona", "valor": _nombre(ep.zona)},
            {"label": "Punto de acceso", "valor": _nombre(ep.punto_acceso)},
            {"label": "Áreas autorizadas", "valor": areas},
            {"label": "Estacionamiento", "valor": ep.parking or "—"},
            {"label": "Cajones", "valor": ep.cajones_parking},
            {"label": "Notas", "valor": ep.notas or "—"},
        ]

    # Documentos del empleado requeridos por el evento (con enlace autenticado).
    tipo_ids = set(
        EventoTipoDocumento.objects.filter(evento_id=ev.id).values_list("tipo_documento_id", flat=True)
    )
    grupo_ids = EventoGrupoDocumentos.objects.filter(evento_id=ev.id).values_list("grupo_id", flat=True)
    if grupo_ids:
        tipo_ids.update(
            TipoDocumento.objects.filter(grupo_id__in=list(grupo_ids)).values_list("id", flat=True)
        )
    documentos = []
    if tipo_ids:
        docs = (
            DocumentoEmpleado.objects
            .select_related("tipo_documento")
            .filter(empleado_id=reg.empleado_id, tipo_documento_id__in=tipo_ids)
        )
        documentos = [
            {
                "nombre": d.tipo_documento.nombre,
                "estado": d.get_estado_display(),
                "url": request.build_absolute_uri(f"/api/documentos/{d.id}/download/")
                if request is not None else f"/api/documentos/{d.id}/download/",
            }
            for d in docs
        ]
    return {"tipo": "evento", "titulo": ev.nombre, "campos": campos}, documentos


def _detalle_cita(reg) -> dict:
    c = reg.cita
    return {
        "tipo": "cita",
        "titulo": c.nombre or f"Cita {c.pk}",
        "campos": [
            {"label": "Recinto", "valor": _nombre(c.recinto)},
            {"label": "Ubicación", "valor": _nombre(c.ubicacion)},
            {"label": "Punto de acceso", "valor": _nombre(c.punto_acceso)},
            {"label": "Protocolo", "valor": _nombre(c.protocolo)},
            {"label": "Fecha", "valor": str(c.fecha) if c.fecha else "—"},
            {"label": "Horario", "valor": _horario(c.hora_inicio, c.hora_fin)},
            {"label": "Detalles", "valor": c.detalles or "—"},
        ],
    }


def _detalle_parking(reg) -> dict:
    ep = reg.cajon.evento_proveedor
    ev = ep.evento
    return {
        "tipo": "parking",
        "titulo": "Estacionamiento",
        "campos": [
            {"label": "Evento", "valor": ev.nombre},
            {"label": "Estacionamiento", "valor": ep.parking or "—"},
            {"label": "Placa", "valor": getattr(reg, "placa_vehiculo", None) or "—"},
        ],
    }


def construir_contexto(request, reg) -> dict:
    """Devuelve {contacto, detalle, documentos, historial} para la pantalla de veredicto."""
    contacto, detalle, documentos, historial = {"email": None, "telefono": None}, None, [], []
    try:
        contacto = _contacto(reg)
    except Exception:
        pass
    try:
        historial = _historial(reg)
    except Exception:
        pass
    try:
        if isinstance(reg, RegistroAccesoParking):
            detalle = _detalle_parking(reg)
        elif getattr(reg, "evento_id", None):
            detalle, documentos = _detalle_evento(request, reg)
        elif getattr(reg, "cita_id", None):
            detalle = _detalle_cita(reg)
    except Exception:
        pass
    return {"contacto": contacto, "detalle": detalle, "documentos": documentos, "historial": historial}
