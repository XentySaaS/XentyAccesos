"""URL del panel de proveedores de un tenant (host propio ``<slug>.proveedores.dominio``).

El panel de proveedores vive en su PROPIO subdominio (registrado como ``Domain`` secundario con
``es_panel_proveedores=True``), separado de la operación (``<slug>.dominio``). Todo link que se
envíe a un proveedor (invitación de onboarding, activación, reset, invitación a evento) debe
construirse con este helper — nunca con el host de la petición del admin, que apunta a la operación.

El esquema y el puerto se heredan de la petición (igual que antes: en dev los links conservan
``:8080``); el dominio sale de la tabla ``Domain``, con fallback textual si el registro aún no
existe (``<slug>.dominio`` → ``<slug>.proveedores.dominio``).
"""

from __future__ import annotations


def url_hub_proveedores(request) -> str:
    """URL absoluta del HUB de proveedores (``proveedores.<dominio base>``).

    El hub es transversal (schema public): sirve el selector de espacios Y el onboarding por
    invitación (el token resuelve el tenant, así que no necesita host de tenant). Los links de
    invitación apuntan aquí para estandarizar la entrada de proveedores en un solo host.
    """
    from django.conf import settings

    host = request.get_host()
    _, _, puerto = host.partition(":")
    sufijo = f":{puerto}" if puerto else ""
    return f"{request.scheme}://proveedores.{settings.TENANT_BASE_DOMAIN}{sufijo}"


def url_panel_proveedores(request, tenant=None) -> str:
    """URL absoluta (scheme://host[:puerto]) del panel de proveedores del tenant."""
    tenant = tenant or getattr(request, "tenant", None)
    host = request.get_host()
    sin_puerto, _, puerto = host.partition(":")
    sufijo = f":{puerto}" if puerto else ""

    dominio = None
    if tenant is not None and getattr(tenant, "pk", None):
        from apps.tenants.models import Domain

        d = Domain.objects.filter(tenant=tenant, es_panel_proveedores=True).first()
        dominio = d.domain if d else None

    if dominio is None:
        if ".proveedores." in sin_puerto or sin_puerto.startswith("proveedores."):
            dominio = sin_puerto  # la petición ya llegó al host del panel
        else:
            slug, _, resto = sin_puerto.partition(".")
            dominio = f"{slug}.proveedores.{resto}" if resto else sin_puerto

    return f"{request.scheme}://{dominio}{sufijo}"
