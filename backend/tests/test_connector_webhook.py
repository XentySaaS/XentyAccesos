"""Webhook de estados de entrega del XCC (control plane, schema public).

Cubre el receptor ``ConnectorWebhookView``: verificación HMAC sobre el cuerpo crudo, anti-replay por
nonce, scoping por tenant y actualización del ledger (``DestinatarioMensaje``) que **solo avanza** el
estado (un ``delivered`` tardío no pisa un ``leido``).
"""

import hashlib
import hmac
import json
import time

import pytest
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIRequestFactory

from apps.mensajeria.connector_webhook import ConnectorWebhookView

pytestmark = pytest.mark.django_db

_factory = APIRequestFactory()
_PATH = "/api/mensajeria/connector/webhook/"
_SECRET = "wh-test-secret"


def _firmar(tenant, ts, nonce, body):
    signing = f"POST\n{_PATH}\n{tenant}\n{ts}\n{nonce}\n{hashlib.sha256(body).hexdigest()}"
    return hmac.new(_SECRET.encode(), signing.encode(), hashlib.sha256).hexdigest()


def _post(tenant, payload, *, nonce="n1", ts=None, firma=None):
    body = json.dumps(payload).encode()
    ts = ts or str(int(time.time()))
    firma = firma if firma is not None else _firmar(tenant, ts, nonce, body)
    req = _factory.post(
        _PATH,
        data=body,
        content_type="application/json",
        HTTP_X_XCC_TENANT=tenant,
        HTTP_X_XCC_TIMESTAMP=ts,
        HTTP_X_XCC_NONCE=nonce,
        HTTP_X_XCC_SIGNATURE=firma,
    )
    return ConnectorWebhookView.as_view()(req)


@pytest.fixture(scope="module")
def tenant_wh(django_db_setup, django_db_blocker):
    from apps.tenants.models import ConfiguracionConnector, Tenant
    from apps.tenants.services.provisioning import provisionar_tenant

    slug = "whqa"
    with django_db_blocker.unblock():
        with connection.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{slug}" CASCADE')
        Tenant.objects.filter(schema_name=slug).delete()

        tenant, _ = provisionar_tenant(
            slug=slug,
            dominio="whqa.localhost",
            nombre="WH QA",
            admin_email="admin@whqa.mx",
            admin_nombre="Admin QA",
            verificar_email=True,
        )
        with schema_context(get_public_schema_name()):
            cfg = ConfiguracionConnector.cargar()
            cfg.hmac_secret = _SECRET
            cfg.save()

        yield tenant

        with connection.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{slug}" CASCADE')
        Tenant.objects.filter(pk=tenant.pk).delete()


def _crear_destinatario(schema, external_id, estado):
    from apps.empleados.models import Empleado
    from apps.mensajeria.models import DestinatarioMensaje, Mensaje
    from apps.proveedores.models import CuentaProveedor

    with schema_context(schema):
        cuenta = CuentaProveedor(nombre="Prov", email=f"{external_id.lower()}@e.mx")
        cuenta.set_password("Secreta123!")
        cuenta.save()
        emp = Empleado.objects.create(proveedor=cuenta, nombre="Emp")
        msg = Mensaje.objects.create(cuerpo="hola")
        return DestinatarioMensaje.objects.create(
            mensaje=msg, empleado=emp, external_id=external_id, estado=estado
        ).id


def _estado(schema, dm_id):
    from apps.mensajeria.models import DestinatarioMensaje

    with schema_context(schema):
        return DestinatarioMensaje.objects.get(pk=dm_id).estado


def test_delivered_avanza_a_entregado(tenant_wh):
    from apps.mensajeria.models import DestinatarioMensaje as DM

    dm_id = _crear_destinatario(tenant_wh.schema_name, "MID-DEL", DM.Estado.ENVIADO)
    resp = _post(
        tenant_wh.schema_name,
        {"tenant": tenant_wh.schema_name, "message_id": "MID-DEL", "status": "delivered"},
    )
    assert resp.status_code == 200
    assert resp.data["actualizados"] == 1
    assert _estado(tenant_wh.schema_name, dm_id) == DM.Estado.ENTREGADO


def test_delivered_no_retrocede_desde_leido(tenant_wh):
    from apps.mensajeria.models import DestinatarioMensaje as DM

    dm_id = _crear_destinatario(tenant_wh.schema_name, "MID-READ", DM.Estado.LEIDO)
    resp = _post(
        tenant_wh.schema_name,
        {"tenant": tenant_wh.schema_name, "message_id": "MID-READ", "status": "delivered"},
        nonce="n-read",
    )
    assert resp.status_code == 200
    assert resp.data["actualizados"] == 0  # leido no retrocede a entregado
    assert _estado(tenant_wh.schema_name, dm_id) == DM.Estado.LEIDO


def test_firma_invalida_401(tenant_wh):
    resp = _post(
        tenant_wh.schema_name,
        {"tenant": tenant_wh.schema_name, "message_id": "X", "status": "read"},
        firma="deadbeef",
        nonce="n-bad",
    )
    assert resp.status_code == 401


def test_tenant_del_cuerpo_distinto_al_firmado_403(tenant_wh):
    resp = _post(
        tenant_wh.schema_name,
        {"tenant": "otro", "message_id": "X", "status": "read"},
        nonce="n-cross",
    )
    assert resp.status_code == 403


def test_nonce_replay_401(tenant_wh):
    from apps.mensajeria.models import DestinatarioMensaje as DM

    _crear_destinatario(tenant_wh.schema_name, "MID-RE", DM.Estado.ENVIADO)
    payload = {"tenant": tenant_wh.schema_name, "message_id": "MID-RE", "status": "delivered"}
    ts = str(int(time.time()))
    nonce = "n-replay"
    body = json.dumps(payload).encode()
    firma = _firmar(tenant_wh.schema_name, ts, nonce, body)

    r1 = _post(tenant_wh.schema_name, payload, nonce=nonce, ts=ts, firma=firma)
    r2 = _post(tenant_wh.schema_name, payload, nonce=nonce, ts=ts, firma=firma)
    assert r1.status_code == 200
    assert r2.status_code == 401  # mismo nonce → replay
