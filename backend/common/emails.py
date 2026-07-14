"""Funciones de envío de correo transaccional para Xenty Acceso.

Usado por: apps.proveedores (invitación + activación) y el signup del control plane (verificación).
Todos usan la plantilla HTML de marca (``common.email_builder``), la misma de las notificaciones de
eventos/citas/documentos, con fallback en texto plano para clientes sin HTML.
"""

from __future__ import annotations

import re

from django.conf import settings

from common.email_builder import construir_correo, enviar_correo_html

_STRONG = re.compile(r"</?strong>")


def _plano(saludo: str, parrafos: list[str], *, url: str | None, nombre_tenant: str) -> str:
    """Versión en texto plano (para el fallback del correo y el cuerpo de WhatsApp)."""
    cuerpo = "\n\n".join(_STRONG.sub("", p) for p in parrafos)
    enlace = f"\n\n{url}" if url else ""
    return f"{saludo}\n\n{cuerpo}{enlace}\n\n— {nombre_tenant} · Xenty Acceso"


def _proveedores_url(base_url: str | None = None) -> str:
    """Base del SPA de proveedores.

    Preferimos ``base_url`` (derivado del host de la petición del admin que invita): así el link
    hereda el subdominio del tenant —``<tenant>.dominio``— y Nginx preserva el Host para que
    django-tenants resuelva el tenant. Sin esto, un link a ``localhost`` pierde el contexto de
    tenant y el backend responde 404 ("No tenant for hostname"). El setting queda como fallback
    para contextos sin petición (Celery/ETL).
    """
    base = base_url or getattr(settings, "FRONTEND_PROVEEDORES_URL", "http://localhost:5175")
    return base.rstrip("/")


def _notificar_wa(telefono: str | None, cuerpo: str) -> None:
    """WhatsApp best-effort si el destinatario tiene teléfono (import diferido evita ciclos)."""
    if not telefono:
        return
    from apps.mensajeria.services import notificar_whatsapp

    notificar_whatsapp(telefono, cuerpo)


def enviar_invitacion_proveedor(
    *,
    email_destino: str,
    nombre_empresa: str,
    nombre_tenant: str,
    token: str,
    base_url: str | None = None,
    telefono: str | None = None,
) -> None:
    """Envía la invitación de onboarding al responsable (correo + WhatsApp si tiene teléfono)."""
    url = f"{_proveedores_url(base_url)}/proveedores/onboarding?token={token}"
    asunto = f"Invitación para registrarte como proveedor de {nombre_tenant}"
    saludo = "Hola,"
    parrafos = [
        f"Has sido invitado a registrar a <strong>{nombre_empresa}</strong> como proveedor de "
        f"<strong>{nombre_tenant}</strong>.",
        "Completa tu registro con el siguiente botón (enlace válido <strong>72 horas</strong>).",
        "En el registro podrás cargar tus documentos (REPSE, SUA) y crear tu contraseña de acceso.",
        "Si no esperabas este correo, puedes ignorarlo.",
    ]
    texto_plano = _plano(saludo, parrafos, url=url, nombre_tenant=nombre_tenant)
    html = construir_correo(
        nombre_tenant=nombre_tenant,
        tipo="bienvenida",
        titulo="Te invitamos a registrarte",
        saludo=saludo,
        parrafos=parrafos,
        cta_texto="Completar mi registro",
        cta_url=url,
        asunto=asunto,
        pre_header=f"Regístrate como proveedor de {nombre_tenant} (enlace válido 72 horas).",
        footer_legal="Si no esperabas esta invitación, ignora este correo. Xenty Accesos · Sistema de Control de Acceso.",
    )
    enviar_correo_html(asunto=asunto, texto_plano=texto_plano, html=html, destino=email_destino)
    _notificar_wa(telefono, texto_plano)


def enviar_verificacion_email(
    *,
    email_destino: str,
    nombre: str,
    nombre_tenant: str,
    url: str,
    telefono: str | None = None,
) -> None:
    """Envía el correo de verificación (doble opt-in) al admin de un tenant recién dado de alta.

    También se manda por WhatsApp si el admin tiene teléfono (regla del producto: toda notificación
    va por ambos canales). El enlace confirma el correo igual desde cualquier canal.
    """
    asunto = f"Confirma tu correo — {nombre_tenant} · Xenty Acceso"
    saludo = f"Hola {nombre},"
    parrafos = [
        f"Gracias por registrar <strong>{nombre_tenant}</strong> en Xenty Acceso.",
        "Para activar tu cuenta confirma tu correo con el siguiente botón "
        "(enlace válido <strong>48 horas</strong>).",
        "Si no realizaste este registro, puedes ignorar este mensaje.",
    ]
    texto_plano = _plano(saludo, parrafos, url=url, nombre_tenant=nombre_tenant)
    html = construir_correo(
        nombre_tenant=nombre_tenant,
        tipo="info",
        titulo="Confirma tu correo",
        saludo=saludo,
        parrafos=parrafos,
        cta_texto="Confirmar mi correo",
        cta_url=url,
        asunto=asunto,
        pre_header=f"Confirma tu correo para activar tu cuenta en {nombre_tenant}.",
        footer_legal="Si no realizaste este registro, ignora este mensaje. Xenty Accesos · Sistema de Control de Acceso.",
    )
    enviar_correo_html(asunto=asunto, texto_plano=texto_plano, html=html, destino=email_destino)
    _notificar_wa(telefono, texto_plano)


def enviar_reset_password(
    *,
    email_destino: str,
    nombre: str,
    nombre_tenant: str,
    url: str,
    telefono: str | None = None,
) -> None:
    """Envía el enlace de restablecimiento de contraseña (correo + WhatsApp si tiene teléfono)."""
    asunto = f"Restablece tu contraseña — {nombre_tenant} · Xenty Acceso"
    saludo = f"Hola {nombre}," if nombre else "Hola,"
    parrafos = [
        f"Recibimos una solicitud para restablecer la contraseña de tu cuenta en "
        f"<strong>{nombre_tenant}</strong>.",
        "Usa el siguiente botón para crear una nueva contraseña "
        "(enlace válido <strong>1 hora</strong>).",
        "Si no solicitaste este cambio, ignora este mensaje: tu contraseña seguirá siendo la misma.",
    ]
    texto_plano = _plano(saludo, parrafos, url=url, nombre_tenant=nombre_tenant)
    html = construir_correo(
        nombre_tenant=nombre_tenant,
        tipo="info",
        titulo="Restablece tu contraseña",
        saludo=saludo,
        parrafos=parrafos,
        cta_texto="Restablecer mi contraseña",
        cta_url=url,
        asunto=asunto,
        pre_header=f"Restablece la contraseña de tu cuenta en {nombre_tenant} (enlace válido 1 hora).",
        footer_legal="Si no solicitaste este cambio, ignora este mensaje. Xenty Accesos · Sistema de Control de Acceso.",
    )
    enviar_correo_html(asunto=asunto, texto_plano=texto_plano, html=html, destino=email_destino)
    _notificar_wa(telefono, texto_plano)


def enviar_activacion_proveedor(
    *,
    email_destino: str,
    nombre_responsable: str,
    nombre_empresa: str,
    nombre_tenant: str,
    base_url: str | None = None,
    telefono: str | None = None,
) -> None:
    """Notifica al responsable que su cuenta fue activada (correo + WhatsApp si tiene teléfono)."""
    url = f"{_proveedores_url(base_url)}/proveedores"
    asunto = f"Tu acceso como proveedor de {nombre_tenant} está listo"
    saludo = f"Hola {nombre_responsable},"
    parrafos = [
        f"Tu registro como proveedor de <strong>{nombre_empresa}</strong> en "
        f"<strong>{nombre_tenant}</strong> ha sido aprobado.",
        "Ya puedes acceder al panel de proveedores.",
        "Ingresa con el correo y la contraseña que registraste durante el onboarding.",
    ]
    texto_plano = _plano(saludo, parrafos, url=url, nombre_tenant=nombre_tenant)
    html = construir_correo(
        nombre_tenant=nombre_tenant,
        tipo="bienvenida",
        titulo="Tu acceso está listo",
        saludo=saludo,
        parrafos=parrafos,
        cta_texto="Ir al panel de proveedor",
        cta_url=url,
        asunto=asunto,
        pre_header=f"Tu acceso como proveedor de {nombre_tenant} ya está activo.",
        footer_legal="Xenty Accesos · Sistema de Control de Acceso.",
    )
    enviar_correo_html(asunto=asunto, texto_plano=texto_plano, html=html, destino=email_destino)
    _notificar_wa(telefono, texto_plano)
