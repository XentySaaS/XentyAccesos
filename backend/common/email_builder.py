"""Constructor de correos HTML para Xenty Acceso — diseño «Xenty Accesos» (oscuro, unificado).

Un único shell de marca para todas las notificaciones: cabecera con logo, barra de acento por tipo,
hero (ícono + título + subtítulo), tarjeta de datos (filas etiqueta/valor), bloque de mensaje opcional,
botón CTA y pie. **Todo con estilos inline y layout por tablas** para compatibilidad con Gmail, Outlook
y Apple Mail (nada de flexbox ni `<style>` en `<head>`).

Cada notificación elige un ``tipo`` (acento + ícono). API:

    html = construir_correo(
        nombre_tenant="Museos",
        tipo="acceso",
        titulo="Tu acceso está confirmado",
        subtitulo="Presenta el gafete en la entrada.",
        filas=[
            {"label": "Invitado", "valor": "María G."},
            {"label": "Evento", "valor": "Gran Evento"},
            {"label": "Zona", "valor": "NORTE", "color": "#FFD700"},
            {"label": "Código", "valor": "XENTY-…", "mono": True, "full": True},
        ],
        card_titulo="Detalles del acceso",
        mensaje="El acceso es intransferible.",
        cta_texto="Ver mi gafete", cta_url="https://…",
        asunto="Invitación",
    )

Compatibilidad hacia atrás: los llamadores antiguos que pasan ``saludo`` + ``parrafos`` siguen
funcionando; ese contenido se renderiza como cuerpo de texto bajo el hero.
"""

from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

# ─── Paleta (tokens del diseño Xenty Accesos) ────────────────────────────────
_BG = "#0D0D14"  # fondo del correo
_BG_HEAD = "#090910"
_BG_FOOT = "#07070E"
_BG_OUT = "#15151E"  # fondo exterior (área alrededor de la tarjeta)
_CARD = "rgba(255,255,255,0.04)"
_BD_CARD = "rgba(255,255,255,0.07)"
_BD_ROW = "rgba(255,255,255,0.05)"
_BD_HEAD = "rgba(255,255,255,0.06)"
_WHITE = "#ffffff"
_MUTED = "rgba(255,255,255,0.50)"
_LABEL = "rgba(255,255,255,0.28)"
_FOOT = "rgba(255,255,255,0.20)"
_FOOT_LOGO = "rgba(255,255,255,0.40)"
_FONT = "'Inter', Arial, Helvetica, sans-serif"
_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]  # fmt: skip


# ─── Íconos SVG por tipo (28×28, sin dependencias externas) ──────────────────
def _icono_check(color: str) -> str:
    return (
        f'<svg width="28" height="28" viewBox="0 0 28 28" fill="none">'
        f'<circle cx="14" cy="14" r="10" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'<path d="M8.5 14l4 4.5 7-9" stroke="{color}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


_ICON_PARKING = (
    '<svg width="30" height="22" viewBox="0 0 30 22" fill="none">'
    '<rect x="2" y="7" width="26" height="11" rx="3" fill="rgba(255,215,0,0.6)"/>'
    '<path d="M5 7l3-5h14l3 5" stroke="rgba(255,215,0,0.6)" stroke-width="1.5" '
    'stroke-linejoin="round" fill="none"/>'
    '<circle cx="8" cy="19" r="3" fill="#FFD700"/>'
    '<circle cx="22" cy="19" r="3" fill="#FFD700"/></svg>'
)
_ICON_CLOCK = (
    '<svg width="28" height="28" viewBox="0 0 28 28" fill="none">'
    '<circle cx="14" cy="14" r="10" fill="none" stroke="#42A5F5" stroke-width="1.5"/>'
    '<path d="M14 8v6.5l4 2.5" stroke="#42A5F5" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
_ICON_WARN = (
    '<svg width="28" height="28" viewBox="0 0 28 28" fill="none">'
    '<circle cx="14" cy="14" r="10" fill="none" stroke="#FF6D00" stroke-width="1.5"/>'
    '<path d="M14 8v8M14 19v1" stroke="#FF6D00" stroke-width="2.2" stroke-linecap="round"/></svg>'
)
_ICON_X = (
    '<svg width="28" height="28" viewBox="0 0 28 28" fill="none">'
    '<circle cx="14" cy="14" r="10" fill="none" stroke="#EF5350" stroke-width="1.5"/>'
    '<path d="M10 10l8 8M18 10l-8 8" stroke="#EF5350" stroke-width="2.2" stroke-linecap="round"/></svg>'
)
_ICON_INFO = (
    '<svg width="28" height="28" viewBox="0 0 28 28" fill="none">'
    '<circle cx="14" cy="14" r="10" fill="none" stroke="#42A5F5" stroke-width="1.5"/>'
    '<path d="M14 13v6M14 9v0.5" stroke="#42A5F5" stroke-width="2.2" stroke-linecap="round"/></svg>'
)

# ─── Registro de tipos (acento + ícono + colores derivados) ──────────────────
_GOLD = "linear-gradient(90deg,#8B6400,#FFD700,#FFA200)"
_TIPOS: dict[str, dict] = {
    # 1a — confirmación de acceso / gafete listo
    "acceso": {
        "accent": _GOLD,
        "icon": _icono_check("#FFD700"),
        "icon_bg": "rgba(255,215,0,0.10)",
        "icon_bd": "rgba(255,215,0,0.25)",
        "cta_text": "#000000",
        "msg_bg": "rgba(255,215,0,0.07)",
        "msg_bd": "rgba(255,215,0,0.15)",
    },
    # 1b — pase de estacionamiento
    "parking": {
        "accent": _GOLD,
        "icon": _ICON_PARKING,
        "icon_bg": "rgba(255,215,0,0.10)",
        "icon_bd": "rgba(255,215,0,0.25)",
        "cta_text": "#000000",
        "msg_bg": "rgba(255,215,0,0.07)",
        "msg_bd": "rgba(255,215,0,0.15)",
    },
    # 1c — recordatorio de evento
    "recordatorio": {
        "accent": "linear-gradient(90deg,#0D47A1,#1565C0,#42A5F5)",
        "icon": _ICON_CLOCK,
        "icon_bg": "rgba(66,165,245,0.10)",
        "icon_bd": "rgba(66,165,245,0.25)",
        "cta_text": "#ffffff",
        "msg_bg": "rgba(66,165,245,0.07)",
        "msg_bd": "rgba(66,165,245,0.15)",
    },
    # 1d — cancelación / modificación
    "modificacion": {
        "accent": "linear-gradient(90deg,#E65100,#FF6D00,#FFA726)",
        "icon": _ICON_WARN,
        "icon_bg": "rgba(255,109,0,0.10)",
        "icon_bd": "rgba(255,109,0,0.25)",
        "cta_text": "#ffffff",
        "msg_bg": "rgba(255,109,0,0.07)",
        "msg_bd": "rgba(255,109,0,0.15)",
    },
    # 1e — alerta de seguridad / acceso denegado
    "alerta": {
        "accent": "linear-gradient(90deg,#B71C1C,#D32F2F,#EF5350)",
        "icon": _ICON_X,
        "icon_bg": "rgba(239,83,80,0.10)",
        "icon_bd": "rgba(239,83,80,0.25)",
        "cta_text": "#ffffff",
        "msg_bg": "rgba(239,83,80,0.07)",
        "msg_bd": "rgba(239,83,80,0.15)",
    },
    # 1f — bienvenida / registro exitoso
    "bienvenida": {
        "accent": "linear-gradient(90deg,#1B5E20,#2E7D32,#00C853)",
        "icon": _icono_check("#00C853"),
        "icon_bg": "rgba(0,200,83,0.10)",
        "icon_bd": "rgba(0,200,83,0.25)",
        "cta_text": "#ffffff",
        "msg_bg": "rgba(0,200,83,0.07)",
        "msg_bd": "rgba(0,200,83,0.12)",
    },
    # neutro — correos de cuenta/seguridad que no encajan en los 6 de acceso (reset, verificación)
    "info": {
        "accent": "linear-gradient(90deg,#0D47A1,#1565C0,#42A5F5)",
        "icon": _ICON_INFO,
        "icon_bg": "rgba(66,165,245,0.10)",
        "icon_bd": "rgba(66,165,245,0.25)",
        "cta_text": "#ffffff",
        "msg_bg": "rgba(66,165,245,0.07)",
        "msg_bd": "rgba(66,165,245,0.15)",
    },
}


# Color sólido de respaldo por tipo (clientes que no renderizan gradientes, p. ej. Outlook):
# la barra de acento y el botón usan este color como `background-color` para no caer a dorado.
_SOLID = {
    "acceso": "#FFD700",
    "parking": "#FFD700",
    "recordatorio": "#1565C0",
    "modificacion": "#FF6D00",
    "alerta": "#D32F2F",
    "bienvenida": "#2E7D32",
    "info": "#1565C0",
}


def _fecha_larga() -> str:
    ahora = datetime.now()
    return f"{ahora.day} de {_MESES[ahora.month - 1]}, {ahora.year}"


# ─── Bloques (HTML por tablas) ───────────────────────────────────────────────
def _header(nombre_tenant: str) -> str:
    logo = (
        '<svg width="32" height="32" viewBox="0 0 32 32" fill="none">'
        '<rect width="32" height="32" rx="7" fill="#FFD700"/>'
        '<circle cx="16" cy="16" r="9" fill="none" stroke="#000" stroke-width="1.5"/>'
        '<path d="M10.5 16l4 4.5 7-9" stroke="#000" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    return f"""
    <tr><td style="background:{_BG_HEAD};padding:22px 36px;border-bottom:1px solid {_BD_HEAD};">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td align="left" style="vertical-align:middle;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
            <td style="vertical-align:middle;padding-right:10px;">{logo}</td>
            <td style="vertical-align:middle;">
              <div style="font-size:15px;font-weight:900;color:{_WHITE};letter-spacing:0.04em;">XENTY</div>
              <div style="font-size:7.5px;font-weight:600;color:rgba(255,255,255,0.3);letter-spacing:0.18em;text-transform:uppercase;margin-top:1px;">Accesos</div>
            </td>
          </tr></table>
        </td>
        <td align="right" style="vertical-align:middle;font-size:10px;color:rgba(255,255,255,0.25);">{_fecha_larga()}</td>
      </tr></table>
    </td></tr>"""


def _hero(t: dict, titulo: str, subtitulo: str) -> str:
    sub = (
        f'<p style="font-size:13px;color:{_MUTED};line-height:1.6;margin:0 auto;max-width:420px;">{subtitulo}</p>'
        if subtitulo
        else ""
    )
    return f"""
    <tr><td style="padding:36px 36px 28px;text-align:center;">
      <table role="presentation" align="center" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto 20px;"><tr>
        <td width="64" height="64" align="center" valign="middle"
            style="width:64px;height:64px;border-radius:16px;background:{t["icon_bg"]};border:1px solid {t["icon_bd"]};text-align:center;">
          {t["icon"]}
        </td>
      </tr></table>
      <h1 style="font-size:22px;font-weight:900;color:{_WHITE};line-height:1.2;margin:0 0 10px;letter-spacing:0.01em;">{titulo}</h1>
      {sub}
    </td></tr>"""


def _celda(cell: dict, con_borde_izq: bool, ancho: str) -> str:
    es_mono = bool(cell.get("mono"))
    color = cell.get("color", _WHITE)
    fam = "font-family:ui-monospace,Menlo,Consolas,monospace;" if es_mono else ""
    peso = "500" if es_mono else "700"
    tam = "11px" if es_mono else ("20px" if cell.get("grande") else "12.5px")
    bl = f"border-left:1px solid {_BD_ROW};" if con_borde_izq else ""
    return (
        f'<td width="{ancho}" style="padding:12px 18px;vertical-align:top;{bl}">'
        f'<div style="font-size:7.5px;font-weight:700;letter-spacing:0.16em;color:{_LABEL};text-transform:uppercase;margin-bottom:4px;">{cell["label"]}</div>'
        f'<div style="{fam}font-size:{tam};font-weight:{peso};color:{color};line-height:1.3;word-break:break-word;">{cell["valor"]}</div>'
        f"</td>"
    )


def _empaquetar_filas(filas: list[dict]) -> list[list[dict]]:
    """Agrupa las celdas en filas de 2, salvo las marcadas ``full`` (ocupan la fila completa)."""
    rows: list[list[dict]] = []
    buf: list[dict] = []
    for cell in filas:
        if cell.get("full"):
            if buf:
                rows.append(buf)
                buf = []
            rows.append([cell])
        else:
            buf.append(cell)
            if len(buf) == 2:
                rows.append(buf)
                buf = []
    if buf:
        rows.append(buf)
    return rows


def _card(card_titulo: str, filas: list[dict]) -> str:
    rows = _empaquetar_filas(filas)
    filas_html = []
    for i, row in enumerate(rows):
        borde = "" if i == len(rows) - 1 else f"border-bottom:1px solid {_BD_ROW};"
        if len(row) == 1:
            celdas = _celda(row[0], False, "100%")
        else:
            celdas = _celda(row[0], False, "50%") + _celda(row[1], True, "50%")
        filas_html.append(
            f'<tr style="{borde}"><td style="padding:0;{borde}"><table role="presentation" '
            f'width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{celdas}</tr></table></td></tr>'
        )
    head = (
        f'<tr><td style="padding:13px 18px;border-bottom:1px solid {_BD_HEAD};">'
        f'<div style="font-size:8.5px;font-weight:700;letter-spacing:0.2em;color:rgba(255,255,255,0.3);text-transform:uppercase;">{card_titulo}</div>'
        f"</td></tr>"
        if card_titulo
        else ""
    )
    return f"""
    <tr><td style="padding:0 36px 24px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:{_CARD};border:1px solid {_BD_CARD};border-radius:12px;">
        {head}
        {"".join(filas_html)}
      </table>
    </td></tr>"""


def _mensaje(t: dict, texto: str) -> str:
    return f"""
    <tr><td style="padding:0 36px 24px;">
      <div style="padding:16px 18px;border-radius:10px;background:{t["msg_bg"]};border:1px solid {t["msg_bd"]};font-size:12px;line-height:1.65;color:{_MUTED};">{texto}</div>
    </td></tr>"""


def _cuerpo_parrafos(saludo: str, parrafos: list[str]) -> str:
    if not saludo and not parrafos:
        return ""
    partes = []
    if saludo:
        partes.append(
            f'<p style="margin:0 0 12px;font-size:14px;font-weight:700;color:{_WHITE};line-height:1.4;">{saludo}</p>'
        )
    for p in parrafos:
        partes.append(
            f'<p style="margin:0 0 12px;font-size:13px;color:{_MUTED};line-height:1.7;">{p}</p>'
        )
    return f'<tr><td style="padding:0 36px 24px;">{"".join(partes)}</td></tr>'


def _cta(t: dict, texto: str, url: str, solid: str) -> str:
    return f"""
    <tr><td style="padding:4px 36px 32px;text-align:center;">
      <a href="{url}" style="display:inline-block;padding:13px 32px;border-radius:9px;background:{t["accent"]};background-color:{solid};font-size:13px;font-weight:700;letter-spacing:0.05em;text-decoration:none;color:{t["cta_text"]};">{texto}</a>
    </td></tr>"""


def _footer(legal: str, privacy_url: str) -> str:
    link = (
        f'<div style="margin-top:12px;"><a href="{privacy_url}" style="font-size:10px;font-weight:600;color:rgba(255,255,255,0.3);text-decoration:none;">Política de privacidad</a></div>'
        if privacy_url
        else ""
    )
    return f"""
    <tr><td style="background:{_BG_FOOT};padding:22px 36px;border-top:1px solid {_BD_HEAD};">
      <div style="font-size:11px;font-weight:800;color:{_FOOT_LOGO};letter-spacing:0.08em;margin-bottom:8px;">XENTY ACCESOS</div>
      <div style="font-size:10px;line-height:1.6;color:{_FOOT};">{legal}</div>
      {link}
    </td></tr>"""


# ─── API pública ─────────────────────────────────────────────────────────────
def construir_correo(
    *,
    nombre_tenant: str,
    saludo: str = "",
    parrafos: list[str] | None = None,
    cta_texto: str | None = None,
    cta_url: str | None = None,
    logo_url: str | None = None,  # aceptado por compat; el shell usa el logo Xenty
    asunto: str = "",
    tipo: str = "acceso",
    titulo: str | None = None,
    subtitulo: str | None = None,
    filas: list[dict] | None = None,
    card_titulo: str = "",
    mensaje: str | None = None,
    pre_header: str = "",
    footer_legal: str | None = None,
    privacy_url: str = "",
) -> str:
    """Devuelve el HTML completo del correo con el shell «Xenty Accesos».

    Args:
        nombre_tenant: Nombre del tenant (marca del remitente).
        tipo: clave de acento/ícono en ``_TIPOS`` (``acceso``/``parking``/``recordatorio``/
            ``modificacion``/``alerta``/``bienvenida``/``info``).
        titulo/subtitulo: hero. Si no hay ``titulo``, usa ``asunto``.
        filas: celdas de la tarjeta (``{label, valor, color?, mono?, grande?, full?}``).
        card_titulo: encabezado de la tarjeta (vacío = sin encabezado).
        mensaje: bloque de mensaje contextual (HTML permitido).
        saludo/parrafos: contenido de texto (compat con llamadores antiguos).
        cta_texto/cta_url: botón de acción.
        pre_header: texto de preview oculto (≤90 car.).
        footer_legal: texto legal del pie (por defecto uno genérico).
    """
    t = _TIPOS.get(tipo, _TIPOS["acceso"])
    titulo = titulo or asunto or "Notificación"
    parrafos = parrafos or []
    legal = footer_legal or (
        "Notificación automática de Xenty Accesos · Sistema de Control de Acceso. "
        "El acceso es intransferible y válido únicamente para el titular registrado."
    )

    solid = _SOLID.get(tipo, "#FFD700")
    partes = [
        _header(nombre_tenant),
        f'<tr><td style="height:4px;font-size:0;line-height:0;background:{t["accent"]};background-color:{solid};">&nbsp;</td></tr>',
    ]
    partes.append(_hero(t, titulo, subtitulo or ""))
    if filas:
        partes.append(_card(card_titulo or "Detalles", filas))
    if mensaje:
        partes.append(_mensaje(t, mensaje))
    cuerpo = _cuerpo_parrafos(saludo, parrafos)
    if cuerpo:
        partes.append(cuerpo)
    if cta_texto and cta_url:
        partes.append(_cta(t, cta_texto, cta_url, solid))
    partes.append(
        f'<tr><td style="padding:0 36px 24px;"><div style="height:1px;background:{_BD_HEAD};font-size:0;line-height:0;">&nbsp;</div></td></tr>'
    )
    partes.append(_footer(legal, privacy_url))

    pre = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{pre_header}</div>'
        if pre_header
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="color-scheme" content="dark"/>
<meta name="supported-color-schemes" content="dark"/>
<title>{titulo}</title>
</head>
<body style="margin:0;padding:0;background:{_BG_OUT};font-family:{_FONT};">
{pre}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_BG_OUT};">
  <tr><td align="center" style="padding:24px 12px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
           style="width:600px;max-width:600px;background:{_BG};border-radius:16px;overflow:hidden;">
      {"".join(partes)}
    </table>
  </td></tr>
</table>
</body></html>"""


def enviar_correo_html(
    *,
    asunto: str,
    texto_plano: str,
    html: str,
    destino: str | None,
    adjuntos: list[tuple[str, bytes, str]] | None = None,
    from_email: str | None = None,
) -> None:
    """Envía un correo HTML con fallback en texto plano. Best-effort (no lanza)."""
    if not destino:
        return
    remitente = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@xenty.mx")
    logger.info("Intentando enviar correo a %s asunto=%r", destino, asunto)
    try:
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano,
            from_email=remitente,
            to=[destino],
        )
        msg.attach_alternative(html, "text/html")
        if adjuntos:
            for nombre_f, datos, ct in adjuntos:
                msg.attach(nombre_f, datos, ct)
        msg.send(fail_silently=False)
        logger.info("Correo enviado correctamente a %s", destino)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Correo HTML no enviado a %s: %s", destino, exc)
