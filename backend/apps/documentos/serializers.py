"""Serializers del catálogo documental y de documentos de empleado."""
from __future__ import annotations

import os

from rest_framework import serializers

from common.validators import validar_archivo

from .models import DocumentoEmpleado, GrupoDocumentos, TipoDocumento


class GrupoDocumentosSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoDocumentos
        fields = ["id", "nombre", "descripcion", "activo"]


class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ["id", "grupo", "nombre", "descripcion", "activo"]


class DocumentoEmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoEmpleado
        fields = [
            "id", "empleado", "tipo_documento", "archivo", "tipo_archivo",
            "estado", "motivo_rechazo", "creado",
        ]
        read_only_fields = ["tipo_archivo", "estado", "motivo_rechazo", "creado"]

    def validate_archivo(self, archivo):
        validar_archivo(archivo, extensiones=(".pdf", ".jpg", ".jpeg", ".png"), max_mb=2)
        return archivo

    def create(self, validated):
        validated["tipo_archivo"] = os.path.splitext(validated["archivo"].name)[1].lstrip(".").lower()
        return super().create(validated)
