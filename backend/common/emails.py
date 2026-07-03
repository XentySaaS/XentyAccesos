"""Funciones de envío de correo transaccional para Xenty Acceso.

Usado por: apps.proveedores (invitación + activación).
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail


def _from() -> str:
    return getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@xenty.mx")


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
    cuerpo = (
        f"Hola,\n\n"
        f"Has sido invitado a registrar a {nombre_empresa} como proveedor de {nombre_tenant}.\n\n"
        f"Completa tu registro en el siguiente enlace (válido 72 horas):\n\n"
        f"  {url}\n\n"
        f"En el registro podrás cargar tus documentos (REPSE, SUA) y crear tu contraseña de acceso.\n\n"
        f"Si no esperabas este correo puedes ignorarlo.\n\n"
        f"— {nombre_tenant} · Xenty Acceso"
    )
    try:
        send_mail(asunto, cuerpo, _from(), [email_destino], fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).error("Error enviando invitación a %s: %s", email_destino, exc)
    _notificar_wa(telefono, cuerpo)


def enviar_verificacion_email(
    *,
    email_destino: str,
    nombre: str,
    nombre_tenant: str,
    url: str,
) -> None:
    """Envía el correo de verificación (doble opt-in) al admin de un tenant recién dado de alta."""
    asunto = f"Confirma tu correo — {nombre_tenant} · Xenty Acceso"
    cuerpo = (
        f"Hola {nombre},\n\n"
        f"Gracias por registrar {nombre_tenant} en Xenty Acceso.\n\n"
        f"Para activar tu cuenta confirma tu correo en el siguiente enlace (válido 48 horas):\n\n"
        f"  {url}\n\n"
        f"Si no realizaste este registro puedes ignorar este mensaje.\n\n"
        f"— Xenty Acceso"
    )
    try:
        send_mail(asunto, cuerpo, _from(), [email_destino], fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).error(
            "Error enviando verificación a %s: %s", email_destino, exc
        )


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
    cuerpo = (
        f"Hola {nombre_responsable},\n\n"
        f"Tu registro como proveedor de {nombre_empresa} en {nombre_tenant} ha sido aprobado.\n\n"
        f"Ya puedes acceder al panel de proveedores:\n\n"
        f"  {url}\n\n"
        f"Ingresa con el correo y contraseña que registraste durante el onboarding.\n\n"
        f"— {nombre_tenant} · Xenty Acceso"
    )
    try:
        send_mail(asunto, cuerpo, _from(), [email_destino], fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).error("Error enviando activación a %s: %s", email_destino, exc)
    _notificar_wa(telefono, cuerpo)
