"""Preferencia de proveedores de WhatsApp del tenant (ARQUITECTURA_CONNECTOR §8.2).

El admin del tenant elige qué proveedores usar y en qué orden (failover). Vive en el schema del
tenant; solo el administrador la edita. Expone además qué proveedores están **disponibles** hoy
(implementados + master switch global del Connector) para que la UI no ofrezca opciones muertas.
"""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import (
    PERMISOS_BASE,
    ContextoAcceso,
    RequiereModulo,
    RequiereRol,
)

from .models import PreferenciaMensajeria
from .proveedores import registro_proveedores

# Etiquetas para la UI (clave → nombre legible). "xcc" es el Connector de respaldo.
_ETIQUETAS = {
    "ultramsg": "UltraMsg (nube)",
    "xcc": "Xenty Connector (respaldo)",
    "sandbox": "Sandbox (pruebas)",
}


def _disponibles() -> list[dict]:
    """Proveedores que el Router puede usar hoy: implementados y —para xcc— habilitados en global."""
    from django_tenants.utils import get_public_schema_name, schema_context

    from apps.tenants.models import ConfiguracionConnector

    registrados = set(registro_proveedores().keys())
    with schema_context(get_public_schema_name()):
        cfg = ConfiguracionConnector.objects.first()
        xcc_on = bool(cfg and cfg.habilitado)
    if xcc_on:
        registrados.add("xcc")  # el Connector se ofrece aunque su provider llegue en F-D
    orden_ui = ["ultramsg", "xcc", "sandbox"]
    return [{"clave": c, "etiqueta": _ETIQUETAS.get(c, c)} for c in orden_ui if c in registrados]


class PreferenciaMensajeriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreferenciaMensajeria
        fields = [
            "proveedores_orden",
            "failover_habilitado",
            "reintentos",
            "timeout_ms",
            "actualizado",
        ]
        read_only_fields = ["actualizado"]

    def validate_proveedores_orden(self, value):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise serializers.ValidationError("Debe ser una lista de claves de proveedor.")
        validas = {d["clave"] for d in _disponibles()}
        invalidas = [v for v in value if v not in validas]
        if invalidas:
            raise serializers.ValidationError(
                f"Proveedores no disponibles: {', '.join(invalidas)}."
            )
        return value


class PreferenciaMensajeriaView(APIView):
    """GET/PUT /api/mensajeria/preferencia/ — orden de proveedores y failover del tenant (admin)."""

    permission_classes = [
        *PERMISOS_BASE(),
        ContextoAcceso,
        RequiereModulo("mensajeria"),
        RequiereRol("administrador"),
    ]

    def get(self, request):
        pref = PreferenciaMensajeria.cargar()
        data = PreferenciaMensajeriaSerializer(pref).data
        data["proveedores_disponibles"] = _disponibles()
        return Response(data)

    def put(self, request):
        pref = PreferenciaMensajeria.cargar()
        s = PreferenciaMensajeriaSerializer(pref, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        data = PreferenciaMensajeriaSerializer(pref).data
        data["proveedores_disponibles"] = _disponibles()
        return Response(data)
