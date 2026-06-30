"""Constructor de correos HTML para Xenty Acceso.

Genera correos responsive con encabezado de marca, tarjeta de contenido y
botón de acción opcional. Todos los estilos son inline para máxima
compatibilidad con clientes de correo (Gmail, Outlook, Apple Mail).

Uso:
    from common.email_builder import construir_correo, enviar_correo_html

    html = construir_correo(
        nombre_tenant="Rayados",
        saludo="Hola Mauricio,",
        parrafos=["Fuiste asignado al evento…"],
        cta_texto="Ver mi acceso",
        cta_url="https://rayados.xenty.mx/proveedores/eventos",
    )
    enviar_correo_html(
        asunto="Tu gafete de acceso — Copa",
        texto_plano="Hola Mauricio, fuiste asignado…",
        html=html,
        destino="mauricio@empresa.com",
    )
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

# ─── Paleta ──────────────────────────────────────────────────────────────────
_NAVY   = "#0F1B2D"
_BLUE   = "#2563EB"
_CARD   = "#ffffff"
_BG     = "#F1F4F8"
_MUTED  = "#64748b"
_TEXT   = "#1e293b"
_BORDER = "#e2e8f0"

# ─── Template base ───────────────────────────────────────────────────────────
_TEMPLATE = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="es">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{asunto}</title>
</head>
<body style="margin:0;padding:0;background-color:{bg};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">

  <!-- Wrapper -->
  <table border="0" cellpadding="0" cellspacing="0" width="100%"
         style="background-color:{bg};min-height:100vh;">
    <tr>
      <td align="center" valign="top" style="padding:0;">

        <!-- ── ENCABEZADO ──────────────────────────────────────────── -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%"
               style="background:{navy};background:linear-gradient(160deg,#0F1B2D 0%,#162f4e 60%,#1a3a5e 100%);">
          <tr>
            <td align="center" style="padding:48px 24px 72px;">

              <!-- Logo / nombre del tenant -->
              {logo_bloque}

              <!-- Sistema -->
              <p style="margin:8px 0 0;color:#94a3b8;font-size:13px;
                         letter-spacing:1.5px;text-transform:uppercase;font-weight:500;">
                Sistema de Accesos &nbsp;·&nbsp; Xenty
              </p>

            </td>
          </tr>
        </table>

        <!-- ── TARJETA ────────────────────────────────────────────── -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%"
               style="max-width:580px;margin:0 auto;">
          <tr>
            <td style="padding:0 20px;">

              <!-- Card wrapper (margen negativo sobre el header) -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%"
                     style="background:{card};border-radius:16px;
                            margin-top:-40px;
                            box-shadow:0 4px 32px rgba(0,0,0,0.12);
                            border:1px solid {border};
                            overflow:hidden;">
                <tr>
                  <td style="padding:36px 40px 32px;">

                    <!-- Saludo -->
                    <p style="margin:0 0 16px;color:{text};font-size:16px;font-weight:700;
                               line-height:1.4;">
                      {saludo}
                    </p>

                    <!-- Párrafos -->
                    {parrafos_html}

                    <!-- CTA (opcional) -->
                    {cta_html}

                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- ── PIE ──────────────────────────────────────────────── -->
          <tr>
            <td align="center" style="padding:28px 20px 40px;">
              <p style="margin:0;color:{muted};font-size:13px;line-height:1.7;">
                Gracias,<br />
                <strong style="color:{muted};">{nombre_tenant}</strong>
                &nbsp;·&nbsp; Xenty Acceso
              </p>
              <p style="margin:12px 0 0;color:#94a3b8;font-size:11px;">
                Este es un mensaje automático, no respondas a este correo.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""

_LOGO_TEXTO = """\
<h1 style="margin:0;color:#ffffff;font-size:38px;font-weight:900;
           letter-spacing:2px;text-transform:uppercase;
           text-shadow:0 2px 8px rgba(0,0,0,0.3);">
  {nombre}
</h1>"""

_LOGO_IMAGEN = """\
<img src="{url}" alt="{nombre}" width="180"
     style="display:block;margin:0 auto;max-height:80px;width:auto;" />"""

_PARRAFO = """\
<p style="margin:0 0 14px;color:{text};font-size:15px;line-height:1.7;">{contenido}</p>"""

_CTA = """\
<table border="0" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td align="center" style="padding:24px 0 8px;">
      <a href="{url}"
         style="display:inline-block;background-color:{navy};color:#ffffff;
                font-size:15px;font-weight:600;text-decoration:none;
                padding:14px 36px;border-radius:8px;
                letter-spacing:0.3px;mso-padding-alt:14px 36px;">
        {texto}
      </a>
      <p style="margin:10px 0 0;color:#94a3b8;font-size:12px;">
        O copia este enlace: <br />
        <a href="{url}" style="color:{blue};word-break:break-all;">{url}</a>
      </p>
    </td>
  </tr>
</table>"""


# ─── API pública ─────────────────────────────────────────────────────────────

def construir_correo(
    *,
    nombre_tenant: str,
    saludo: str,
    parrafos: list[str],
    cta_texto: str | None = None,
    cta_url: str | None = None,
    logo_url: str | None = None,
    asunto: str = "",
) -> str:
    """Devuelve el HTML completo del correo.

    Args:
        nombre_tenant: Nombre del tenant (ej. "Rayados").
        saludo: Primera línea destacada (ej. "Hola Juan,").
        parrafos: Lista de párrafos del cuerpo.
        cta_texto: Texto del botón de acción (opcional).
        cta_url: URL del botón de acción (opcional).
        logo_url: URL pública de la imagen del logo (opcional; usa texto si None).
        asunto: Usado como <title> del HTML.
    """
    logo_bloque = (
        _LOGO_IMAGEN.format(url=logo_url, nombre=nombre_tenant)
        if logo_url
        else _LOGO_TEXTO.format(nombre=nombre_tenant)
    )

    parrafos_html = "\n".join(
        _PARRAFO.format(contenido=p, text=_TEXT) for p in parrafos
    )

    cta_html = (
        _CTA.format(url=cta_url, texto=cta_texto, navy=_NAVY, blue=_BLUE)
        if cta_texto and cta_url
        else ""
    )

    return _TEMPLATE.format(
        asunto=asunto,
        bg=_BG,
        navy=_NAVY,
        blue=_BLUE,
        card=_CARD,
        border=_BORDER,
        text=_TEXT,
        muted=_MUTED,
        logo_bloque=logo_bloque,
        nombre_tenant=nombre_tenant,
        saludo=saludo,
        parrafos_html=parrafos_html,
        cta_html=cta_html,
    )


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
    except Exception as exc:  # noqa: BLE001
        logger.warning("Correo HTML no enviado a %s: %s", destino, exc)
