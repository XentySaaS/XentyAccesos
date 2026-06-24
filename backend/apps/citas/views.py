"""ViewSets de citas: Cita (con reglas de borrado), Contacto y AsistenteCita."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.ocr.services import obtener_ocr, validar_seccion
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol
from common.validators import validar_archivo

from .models import AsistenteCita, Cita, Contacto, EmpleadoCita
from .serializers import AsistenteCitaSerializer, CitaSerializer, ContactoSerializer

_ROLES = ("administrador", "editor", "recepcion", "guardia")
_PERMS = [*PERMISOS_BASE(), ContextoAcceso, RequiereModulo("citas"), RequiereRol(*_ROLES)]


class ContactoViewSet(viewsets.ModelViewSet):
    queryset = Contacto.objects.all().order_by("id")
    serializer_class = ContactoSerializer
    permission_classes = _PERMS
    search_fields = ["nombre", "email"]


class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all().order_by("-id")
    serializer_class = CitaSerializer
    permission_classes = _PERMS
    filterset_fields = ["tipo", "tipo_cita", "estado", "recinto", "proveedor"]

    def perform_create(self, serializer):
        cita = serializer.save(creado_por_usuario=self.request.user)
        # Walk-in: crea automáticamente el registro de entrada (SAR_FUNC §7.1).
        if cita.tipo_cita == Cita.TipoCita.WALK_IN:
            from apps.acceso.services import registrar_walkin

            registrar_walkin(cita)

    def perform_destroy(self, instance):
        # No eliminable: tipo proveedor con empleados, o tipo directa con asistentes (SAR_FUNC §7.1).
        if instance.tipo == Cita.Tipo.PROVEEDOR and EmpleadoCita.objects.filter(cita=instance).exists():
            raise PermissionDenied("La cita de proveedor tiene empleados asignados.")
        if instance.tipo == Cita.Tipo.DIRECTA and instance.asistentes.exists():
            raise PermissionDenied("La cita directa tiene asistentes registrados.")
        instance.delete()


class AsistenteCitaViewSet(viewsets.ModelViewSet):
    queryset = AsistenteCita.objects.all().order_by("id")
    serializer_class = AsistenteCitaSerializer
    permission_classes = _PERMS
    filterset_fields = ["cita", "tipo", "estado"]

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser], url_path="ocr-ine")
    def ocr_ine(self, request, pk=None):
        """Captura la INE: OCR (Textract/sandbox) -> ine_data cifrado + imagen en disco privado."""
        asistente = self.get_object()
        imagen = request.FILES.get("imagen")
        if not imagen:
            return Response({"detail": "Falta 'imagen'."}, status=status.HTTP_400_BAD_REQUEST)
        validar_archivo(imagen, extensiones=(".jpg", ".jpeg", ".png"), max_mb=5)

        datos = obtener_ocr().extraer_ine(imagen.read())
        imagen.seek(0)
        if datos.get("seccion") and not validar_seccion(datos["seccion"]):
            return Response({"detail": "Sección INE inválida."}, status=status.HTTP_400_BAD_REQUEST)

        asistente.ine_data = datos
        asistente.numero_identificacion = datos.get("numero") or datos.get("curp")
        asistente.path_ine.save(f"ine_{asistente.id}.jpg", imagen, save=False)  # storage privado
        asistente.ine_capturado = True
        asistente.save()
        return Response({"ine_capturado": True, "datos": datos})
