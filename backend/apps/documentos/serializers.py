"""Serializers del catálogo documental y de documentos de empleado."""
from __future__ import annotations

import os

from rest_framework import serializers

from common.validators import validar_archivo

from .models import DocumentoEmpleado, GrupoDocumentos, Protocolo, TipoDocumento

_DOCS = (".pdf", ".jpg", ".jpeg", ".png")


class GrupoDocumentosSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoDocumentos
        fields = ["id", "nombre", "descripcion", "activo"]


class TipoDocumentoSerializer(serializers.ModelSerializer):
    grupo_nombre = serializers.SerializerMethodField()

    def get_grupo_nombre(self, obj) -> str:
        return obj.grupo.nombre if obj.grupo else ""

    class Meta:
        model = TipoDocumento
        fields = ["id", "grupo", "grupo_nombre", "nombre", "descripcion", "activo"]


class ProtocoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocolo
        fields = ["id", "nombre", "descripcion", "archivo", "estado", "creado"]
        read_only_fields = ["creado"]

    def validate_archivo(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=20)
        return f


class DocumentoEmpleadoSerializer(serializers.ModelSerializer):
    # Nombres embebidos: Acceso verifica sin poder consultar /api/empleados/ (es de proveedores).
    empleado_nombre = serializers.SerializerMethodField()
    tipo_documento_nombre = serializers.SerializerMethodField()
    proveedor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoEmpleado
        fields = [
            "id", "empleado", "empleado_nombre", "tipo_documento", "tipo_documento_nombre",
            "proveedor_nombre", "archivo", "tipo_archivo", "estado", "motivo_rechazo", "creado",
        ]
        read_only_fields = ["tipo_archivo", "estado", "motivo_rechazo", "creado"]

    def get_empleado_nombre(self, obj) -> str:
        return obj.empleado.nombre if obj.empleado_id else ""

    def get_tipo_documento_nombre(self, obj) -> str:
        return obj.tipo_documento.nombre if obj.tipo_documento_id else ""

    def get_proveedor_nombre(self, obj) -> str:
        cuenta = getattr(obj.empleado, "proveedor", None)
        empresa = getattr(cuenta, "proveedor", None)
        return getattr(empresa, "nombre", "") or getattr(cuenta, "nombre", "") or ""

    def validate_archivo(self, archivo):
        validar_archivo(archivo, extensiones=_DOCS, max_mb=2)
        return archivo

    def create(self, validated):
        validated["tipo_archivo"] = os.path.splitext(validated["archivo"].name)[1].lstrip(".").lower()
        return super().create(validated)
