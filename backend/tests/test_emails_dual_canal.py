"""Los wrappers transaccionales de ``common.emails`` mandan por correo y —si hay teléfono— también
por WhatsApp.

Regla del producto: **toda** notificación va por ambos canales cuando el destinatario tiene los dos
configurados. Este test fija el contrato para los cuatro wrappers (invitación/activación de
proveedor, verificación de correo y reset de contraseña) y evita regresiones como la que tenía la
verificación de correo, que solo mandaba email.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def captura(monkeypatch):
    """Intercepta ambos canales sin enviar nada real; devuelve (correos, whatsapps)."""
    correos: list = []
    wapp: list = []
    monkeypatch.setattr("common.emails.enviar_correo_html", lambda **k: correos.append(k))
    monkeypatch.setattr(
        "apps.mensajeria.services.notificar_whatsapp",
        lambda telefono, cuerpo, *a, **k: (wapp.append((telefono, cuerpo)), True)[1],
    )
    return correos, wapp


def _invocar(nombre_wrapper: str, *, telefono):
    """Llama al wrapper indicado con kwargs mínimos válidos y el teléfono dado."""
    from common import emails

    comunes = {"telefono": telefono} if telefono is not None else {}
    if nombre_wrapper == "verificacion":
        emails.enviar_verificacion_email(
            email_destino="a@x.com", nombre="Ana", nombre_tenant="T", url="https://x/v", **comunes
        )
    elif nombre_wrapper == "reset":
        emails.enviar_reset_password(
            email_destino="a@x.com", nombre="Ana", nombre_tenant="T", url="https://x/r", **comunes
        )
    elif nombre_wrapper == "invitacion":
        emails.enviar_invitacion_proveedor(
            email_destino="a@x.com", nombre_empresa="E", nombre_tenant="T", token="tok", **comunes
        )
    elif nombre_wrapper == "activacion":
        emails.enviar_activacion_proveedor(
            email_destino="a@x.com",
            nombre_responsable="Ana",
            nombre_empresa="E",
            nombre_tenant="T",
            **comunes,
        )


@pytest.mark.parametrize("wrapper", ["verificacion", "reset", "invitacion", "activacion"])
def test_wrapper_manda_correo_y_whatsapp(captura, wrapper):
    correos, wapp = captura
    _invocar(wrapper, telefono="8112223344")
    assert len(correos) == 1, f"{wrapper}: debe mandar correo"
    assert len(wapp) == 1, f"{wrapper}: debe mandar WhatsApp con teléfono"
    assert wapp[0][0] == "8112223344"


@pytest.mark.parametrize("wrapper", ["verificacion", "reset", "invitacion", "activacion"])
def test_wrapper_sin_telefono_solo_correo(captura, wrapper):
    correos, wapp = captura
    _invocar(wrapper, telefono=None)
    assert len(correos) == 1, f"{wrapper}: debe mandar correo aun sin teléfono"
    assert wapp == [], f"{wrapper}: sin teléfono no debe intentar WhatsApp"
