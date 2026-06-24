"""OCR de INE detrás de interfaz (AWS Textract), con modo sandbox sin credenciales.

Reemplaza la validación hueca ``validaSeccionINE`` del origen (siempre True) por una real, y
mantiene Textract intercambiable: si no hay credenciales AWS, usa un backend sandbox para dev/test.
El llamador cifra ``ine_data`` al guardarlo (REMEDIACION §A2); aquí no se loguea PII.
"""
from __future__ import annotations

import re

from django.conf import settings

_SECCION_RE = re.compile(r"^\d{1,4}$")


def validar_seccion(seccion: str | None) -> bool:
    """Sección electoral válida: 1 a 4 dígitos, > 0 (validación real, no la hueca del origen)."""
    if not seccion:
        return False
    s = str(seccion).strip()
    return bool(_SECCION_RE.match(s)) and int(s) > 0


class SandboxOCR:
    """Backend de desarrollo: no llama a AWS; devuelve campos de ejemplo deterministas."""

    def extraer_ine(self, imagen_bytes: bytes) -> dict:
        return {
            "nombre": "JUAN PEREZ LOPEZ",
            "curp": "PELJ900101HDFRPN09",
            "fecha_nacimiento": "1990-01-01",
            "sexo": "H",
            "domicilio": "CALLE FALSA 123",
            "seccion": "1234",
            "numero": "IDMEX1234567890",
        }


class TextractOCR:
    """Backend de producción: AWS Textract ``analyze_id`` sobre la imagen de la INE."""

    CAMPOS = {
        "FIRST_NAME": "nombre", "LAST_NAME": "apellidos", "DATE_OF_BIRTH": "fecha_nacimiento",
        "DOCUMENT_NUMBER": "numero", "ADDRESS": "domicilio",
    }

    def extraer_ine(self, imagen_bytes: bytes) -> dict:
        import boto3

        cliente = boto3.client(
            "textract",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        resp = cliente.analyze_id(DocumentPages=[{"Bytes": imagen_bytes}])
        datos: dict = {}
        for doc in resp.get("IdentityDocuments", []):
            for campo in doc.get("IdentityDocumentFields", []):
                clave = campo.get("Type", {}).get("Text")
                valor = campo.get("ValueDetection", {}).get("Text")
                if clave in self.CAMPOS and valor:
                    datos[self.CAMPOS[clave]] = valor
        return datos


def obtener_ocr():
    """Selecciona el backend OCR según haya credenciales AWS (prod) o no (sandbox)."""
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        return TextractOCR()
    return SandboxOCR()
