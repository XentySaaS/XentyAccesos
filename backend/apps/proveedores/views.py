"""Vistas de proveedores: CRUD + invitación (admin) y onboarding público (token firmado)."""
from __future__ import annotations

from django.core import signing
from django.db import connection
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, RequiereModulo, RequiereRol
from common.signing import VIGENCIA_HORAS, firmar_invitacion, leer_invitacion

from .models import CuentaProveedor, Proveedor
from .serializers import OnboardingProveedorSerializer, ProveedorSerializer


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all().order_by("id")
    serializer_class = ProveedorSerializer
    permission_classes = [*PERMISOS_BASE(), RequiereModulo("proveedores"), RequiereRol("administrador")]
    filterset_fields = ["estado", "rfc"]

    @action(detail=True, methods=["post"])
    def invitar(self, request, pk=None):
        """Genera un token de invitación firmado (72h) para que la empresa complete su alta."""
        proveedor = self.get_object()
        token = firmar_invitacion(proveedor.id, connection.schema_name)
        # En prod se envía por email al responsable; aquí se devuelve para el flujo del front.
        return Response({
            "token": token,
            "vigencia_horas": VIGENCIA_HORAS,
            "onboarding_path": "/api/onboarding/proveedor/",
        })


@method_decorator(ratelimit(key="ip", rate="20/h", method="POST", block=True), name="post")
class OnboardingProveedorView(APIView):
    """Alta pública del proveedor mediante invitación firmada. Sin auth, con rate limit."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        s = OnboardingProveedorSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        datos = s.validated_data
        try:
            payload = leer_invitacion(datos["token"])
        except signing.SignatureExpired:
            return Response({"detail": "La invitación expiró."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return Response({"detail": "Invitación inválida."}, status=status.HTTP_400_BAD_REQUEST)

        if payload.get("tenant") != connection.schema_name:
            return Response({"detail": "Invitación de otro tenant."}, status=status.HTTP_400_BAD_REQUEST)

        proveedor = Proveedor.objects.filter(pk=payload.get("proveedor_id")).first()
        if proveedor is None:
            return Response({"detail": "El proveedor ya no existe."}, status=status.HTTP_404_NOT_FOUND)

        cuenta = CuentaProveedor.objects.create_user(
            email=datos["email"],
            nombre=datos["nombre"],
            password=datos["password"],
            apellidos=datos.get("apellidos", ""),
            puesto=datos.get("puesto", ""),
            telefono=datos.get("telefono", ""),
            proveedor=proveedor,
            rol=CuentaProveedor.Rol.ADMIN,
        )
        # Primera cuenta = responsable; el proveedor pasa a confirmado.
        if proveedor.responsable_id is None:
            proveedor.responsable = cuenta
        proveedor.estado = Proveedor.Estado.CONFIRMADO
        proveedor.save(update_fields=["responsable", "estado"])
        return Response({"detail": "Alta completada.", "proveedor": proveedor.id}, status=201)
