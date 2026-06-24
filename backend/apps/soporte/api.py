"""Endpoint de diagnóstico de Mesa de Ayuda (solo Administrador)."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import EmailVerificado, MFASesionCompleta, RequiereRol

from .services import diagnostico_configuracion


class SaludConfiguracionView(APIView):
    """GET /api/soporte/salud/ — salud de configuración del tenant para diagnóstico."""

    permission_classes = [
        IsAuthenticated,
        MFASesionCompleta,
        EmailVerificado,
        RequiereRol("administrador"),
    ]

    def get(self, request):
        return Response(diagnostico_configuracion(request.tenant))
