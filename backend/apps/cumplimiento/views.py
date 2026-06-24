"""Endpoints de cumplimiento 69-B: validar proveedor, consultar EFOS y resultados."""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.proveedores.models import Proveedor
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import ResultadoLista69b, SatEfo
from .serializers import ResultadoLista69bSerializer, SatEfoSerializer
from .services import validar_69b

_PERMS = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("cumplimiento"), RequiereRol("administrador"),
]


class ValidarProveedorView(APIView):
    """POST /api/cumplimiento/validar/<proveedor_id>/ — valida el RFC contra EFOS."""

    permission_classes = _PERMS

    def post(self, request, proveedor_id):
        proveedor = Proveedor.objects.filter(id=proveedor_id).first()
        if proveedor is None:
            return Response({"detail": "Proveedor no encontrado."}, status=404)
        resultado = validar_69b(proveedor)
        return Response(ResultadoLista69bSerializer(resultado).data)


class SatEfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SatEfo.objects.all().order_by("rfc")
    serializer_class = SatEfoSerializer
    permission_classes = _PERMS
    filterset_fields = ["situacion"]
    search_fields = ["rfc"]


class ResultadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ResultadoLista69b.objects.all().order_by("-creado")
    serializer_class = ResultadoLista69bSerializer
    permission_classes = _PERMS
    filterset_fields = ["proveedor", "estado"]
