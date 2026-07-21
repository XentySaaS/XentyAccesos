"""Códigos de respaldo (recovery codes): helpers puros + endpoints generar/regenerar/verificar.

Los endpoints se invocan directamente sobre la vista (sin la pila de permisos), fijando
``request.user``/``request.auth`` a mano. El rate limit se desactiva en esos tests (es un feature
del framework, no lo que se está probando aquí).
"""

from __future__ import annotations

import re

import pytest
from django_tenants.utils import schema_context
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()


def _req(data: dict, user, auth: dict) -> Request:
    r = Request(_factory.post("/x/", data, format="json"), parsers=[JSONParser()])
    r.user = user
    r.auth = auth
    return r


def _usuario(schema_name: str, email: str, password: str = "secreta"):
    from apps.accounts.models import Usuario

    return Usuario.objects.create_user(email=email, nombre="Test", password=password)


# ── Helpers puros ────────────────────────────────────────────────────────────
def test_formato_alfanumerico_y_sin_repetidos():
    from common import backup_codes

    codigos = backup_codes.generar_codigos()
    assert len(codigos) == 10
    assert len(set(codigos)) == 10  # sin duplicados
    for c in codigos:
        assert re.fullmatch(r"[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}", c)


def test_hash_no_contiene_el_codigo_en_claro():
    from common import backup_codes

    h = backup_codes.hash_codigo("ABCD-EFGH-JKMN")
    assert "ABCD" not in h and "ABCDEFGHJKMN" not in h  # solo el hash Argon2, nunca el plano
    assert h.startswith("argon2")


def test_regenerar_consumir_una_sola_vez_e_invalidar(dos_tenants):
    from common import backup_codes

    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(t1.schema_name, "helpers@x.com")
        codigos = backup_codes.regenerar(u.codigos_respaldo)
        assert backup_codes.disponibles(u.codigos_respaldo) == 10

        # Un código válido se consume una vez (aceptado con o sin guiones).
        assert backup_codes.consumir(u.codigos_respaldo, codigos[0].replace("-", "")) is True
        assert backup_codes.disponibles(u.codigos_respaldo) == 9
        # No reutilizable.
        assert backup_codes.consumir(u.codigos_respaldo, codigos[0]) is False
        # Código inexistente.
        assert backup_codes.consumir(u.codigos_respaldo, "ZZZZ-ZZZZ-ZZZZ") is False

        # Regenerar invalida TODOS los anteriores.
        nuevos = backup_codes.regenerar(u.codigos_respaldo)
        assert backup_codes.disponibles(u.codigos_respaldo) == 10
        assert backup_codes.consumir(u.codigos_respaldo, codigos[1]) is False  # viejo ya no sirve
        assert backup_codes.consumir(u.codigos_respaldo, nuevos[0]) is True


# ── Endpoints ────────────────────────────────────────────────────────────────
def test_generar_primera_vez_sin_password(dos_tenants, settings):
    from common.backup_codes_api import GenerarCodigosRespaldoView

    settings.RATELIMIT_ENABLE = False
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(t1.schema_name, "gen@x.com")
        r = GenerarCodigosRespaldoView().post(_req({}, u, {"ctx": "acceso"}))
    assert r.status_code == 200
    assert len(r.data["codigos"]) == 10


def test_regenerar_exige_reautenticacion(dos_tenants, settings):
    from common import backup_codes
    from common.backup_codes_api import GenerarCodigosRespaldoView

    settings.RATELIMIT_ENABLE = False
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(t1.schema_name, "regen@x.com", password="secreta")
        backup_codes.regenerar(u.codigos_respaldo)  # ya existen → regenerar exige password
        assert GenerarCodigosRespaldoView().post(_req({}, u, {"ctx": "acceso"})).status_code == 403
        assert (
            GenerarCodigosRespaldoView()
            .post(_req({"password": "mala"}, u, {"ctx": "acceso"}))
            .status_code
            == 403
        )
        ok = GenerarCodigosRespaldoView().post(_req({"password": "secreta"}, u, {"ctx": "acceso"}))
    assert ok.status_code == 200 and len(ok.data["codigos"]) == 10


def test_verificar_login_consume_y_emite_tokens(dos_tenants, settings):
    from common import backup_codes
    from common.backup_codes_api import VerificarCodigoRespaldoView

    settings.RATELIMIT_ENABLE = False
    t1, _ = dos_tenants
    with schema_context(t1.schema_name):
        u = _usuario(t1.schema_name, "verif@x.com")
        codigos = backup_codes.regenerar(u.codigos_respaldo)

        # Sin sesión MFA pendiente → 400.
        sin_pend = VerificarCodigoRespaldoView().post(
            _req({"codigo": codigos[0]}, u, {"ctx": "acceso"})
        )
        assert sin_pend.status_code == 400

        # Con MFA pendiente + código válido → tokens full.
        ok = VerificarCodigoRespaldoView().post(
            _req({"codigo": codigos[0]}, u, {"ctx": "acceso", "mfa": "pending"})
        )
        assert ok.status_code == 200 and "access" in ok.data

        # El código quedó consumido → segundo intento inválido.
        repetido = VerificarCodigoRespaldoView().post(
            _req({"codigo": codigos[0]}, u, {"ctx": "acceso", "mfa": "pending"})
        )
        assert repetido.status_code == 400
