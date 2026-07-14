"""Teléfonos: formato canónico de 10 dígitos + lada mexicana solo al enviar por WhatsApp.

Xenty opera solo en México: se almacenan 10 dígitos sin lada y la lada se antepone únicamente en
el punto de envío. Aquí se fija ese contrato (``common.phone``) y que ``notificar_whatsapp`` manda
el número con lada al Router (u omite los inválidos).
"""

from __future__ import annotations

from rest_framework import serializers

from common.phone import (
    TelefonoField,
    formato_whatsapp_mx,
    normalizar_telefono,
    solo_digitos,
)


class TestNormalizarTelefono:
    def test_diez_digitos_se_conservan(self):
        assert normalizar_telefono("8112223344") == "8112223344"

    def test_quita_espacios_y_simbolos(self):
        assert normalizar_telefono("55 1234-5678") == "5512345678"
        assert normalizar_telefono("(811) 222 3344") == "8112223344"

    def test_quita_lada_52(self):
        assert normalizar_telefono("528112223344") == "8112223344"

    def test_quita_lada_521_movil(self):
        assert normalizar_telefono("5218112223344") == "8112223344"
        assert normalizar_telefono("+52 1 811 222 3344") == "8112223344"

    def test_invalido_devuelve_vacio(self):
        assert normalizar_telefono("123") == ""
        assert normalizar_telefono("") == ""
        assert normalizar_telefono(None) == ""
        assert normalizar_telefono("81122233445566") == ""


class TestFormatoWhatsAppMx:
    def test_antepone_lada_movil(self):
        assert formato_whatsapp_mx("8112223344") == "5218112223344"

    def test_idempotente_con_numero_ya_formateado(self):
        assert formato_whatsapp_mx("5218112223344") == "5218112223344"
        assert formato_whatsapp_mx("528112223344") == "5218112223344"

    def test_invalido_devuelve_vacio(self):
        assert formato_whatsapp_mx("123") == ""
        assert formato_whatsapp_mx(None) == ""


def test_solo_digitos():
    assert solo_digitos("+52 (811) 222-3344") == "528112223344"
    assert solo_digitos(None) == ""


class _SerConTelefono(serializers.Serializer):
    telefono = TelefonoField(required=False, allow_null=True, allow_blank=True)


class TestTelefonoField:
    def test_normaliza_a_diez_digitos(self):
        s = _SerConTelefono(data={"telefono": "+52 811 222 3344"})
        assert s.is_valid(), s.errors
        assert s.validated_data["telefono"] == "8112223344"

    def test_rechaza_numero_invalido(self):
        s = _SerConTelefono(data={"telefono": "123"})
        assert not s.is_valid()
        assert "telefono" in s.errors

    def test_acepta_vacio(self):
        s = _SerConTelefono(data={"telefono": ""})
        assert s.is_valid(), s.errors
        assert s.validated_data["telefono"] == ""


def test_notificar_whatsapp_antepone_lada(monkeypatch):
    """El teléfono de 10 dígitos guardado se manda al Router con la lada mexicana."""
    from apps.mensajeria import services
    from apps.mensajeria.proveedores import ResultadoEnvio

    capturado = {}

    def _fake_enviar(telefono, cuerpo, archivo=None, **kw):
        capturado["telefono"] = telefono
        return ResultadoEnvio(ok=True, proveedor="sandbox", external_id="x")

    monkeypatch.setattr(services.router, "enviar", _fake_enviar)
    assert services.notificar_whatsapp("8112223344", "hola") is True
    assert capturado["telefono"] == "5218112223344"


def test_notificar_whatsapp_omite_numero_invalido(monkeypatch):
    """Un número que no son 10 dígitos no se manda (ni llega al Router): devuelve False."""
    from apps.mensajeria import services

    llamado = {"si": False}

    def _fake_enviar(*a, **kw):
        llamado["si"] = True
        raise AssertionError("no debería llamarse con un número inválido")

    monkeypatch.setattr(services.router, "enviar", _fake_enviar)
    assert services.notificar_whatsapp("123", "hola") is False
    assert llamado["si"] is False
