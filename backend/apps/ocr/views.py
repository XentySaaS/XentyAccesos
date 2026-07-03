"""Endpoint público de OCR de INE — acepta imagen como multipart/form-data."""

from __future__ import annotations

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.validators import validar_archivo

from .services import obtener_ocr

_EXTS_INE = (".jpg", ".jpeg", ".png")


@method_decorator(ratelimit(key="ip", rate="30/h", method="POST", block=True), name="post")
class ExtraerIneView(APIView):
    """Recibe la foto de una INE (multipart), la procesa con Textract (o sandbox) y devuelve
    los campos extraídos. Pública: se llama desde el wizard de onboarding antes de tener cuenta.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        imagen = request.FILES.get("imagen")
        if not imagen:
            return Response({"detail": "Se requiere el archivo 'imagen'."}, status=400)

        try:
            validar_archivo(imagen, extensiones=_EXTS_INE, max_mb=10)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)

        imagen_bytes = imagen.read()
        ocr = obtener_ocr()
        try:
            datos = ocr.extraer_ine(imagen_bytes)
        except Exception:
            return Response(
                {"detail": "No se pudo procesar la imagen. Intenta con una foto más nítida."},
                status=500,
            )

        return Response(datos)
