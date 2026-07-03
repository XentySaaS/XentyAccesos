"""Endpoints de Mesa de Ayuda (Nivel B, solo Administrador).

Nivel B = diagnóstico de salud de configuración + cliente de la Mesa (probar conexión, enviar
diagnóstico). Nunca toca datos de dominio ni consume créditos (CLAUDE.md §9).
"""
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import EmailVerificado, MFASesionCompleta, RequiereRol

from . import services

_ADMIN = [IsAuthenticated, MFASesionCompleta, EmailVerificado, RequiereRol("administrador")]


class SaludConfiguracionView(APIView):
    """GET /api/soporte/salud/ — salud de configuración del tenant para diagnóstico."""

    permission_classes = _ADMIN

    def get(self, request):
        return Response(services.diagnostico_configuracion(request.tenant))


class _ConfigSerializer(serializers.Serializer):
    base_url = serializers.URLField(required=False, allow_blank=True)
    habilitada = serializers.BooleanField(required=False)
    api_key = serializers.CharField(required=False, allow_blank=True, write_only=True)


class ConfiguracionMesaView(APIView):
    """GET/PUT /api/soporte/configuracion/ — config de conexión a la Mesa (api_key write-only)."""

    permission_classes = _ADMIN

    def get(self, request):
        return Response(services.leer_configuracion(request.tenant))

    def put(self, request):
        s = _ConfigSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(services.guardar_configuracion(request.tenant, **s.validated_data))


class ProbarConexionView(APIView):
    """POST /api/soporte/probar-conexion/ — verifica conectividad con la Mesa."""

    permission_classes = _ADMIN

    def post(self, request):
        return Response(services.probar_conexion(request.tenant))


class EnviarDiagnosticoView(APIView):
    """POST /api/soporte/enviar-diagnostico/ — envía la salud de config a la Mesa."""

    permission_classes = _ADMIN

    def post(self, request):
        return Response(services.enviar_diagnostico(request.tenant))
