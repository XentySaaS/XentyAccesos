"""ViewSets de citas: Cita, Contacto y AsistenteCita."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.config.services import AuditViewSetMixin
from apps.empleados.models import Empleado
from apps.ocr.services import obtener_ocr, validar_seccion
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequierePermisoPersonalizado, RequiereRol
from common.validators import validar_archivo

from .models import AsistenteCita, Cita, Contacto, EmpleadoCita
from .serializers import (
    AsistenteCitaSerializer,
    CitaDetailSerializer,
    CitaListSerializer,
    CitaSerializer,
    ContactoSerializer,
)

_ROLES = ("administrador", "editor", "recepcion", "usuario")
_PERMS = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("citas"),
    RequiereRol(*_ROLES),
    RequierePermisoPersonalizado("citas"),
]


class ContactoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Contacto.objects.all().order_by("id")
    serializer_class = ContactoSerializer
    permission_classes = _PERMS
    search_fields = ["nombre", "email"]


class CitaViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Cita.objects.none()  # sobreescrito por get_queryset; necesario para el router
    permission_classes = _PERMS
    filterset_fields = ["tipo", "tipo_cita", "estado", "recinto", "proveedor"]

    def get_queryset(self):
        qs = Cita.objects.select_related(
            "recinto", "proveedor", "asignado_a", "protocolo", "ubicacion", "acceso"
        ).order_by("-id")
        if self.request.user.rol != Usuario.Rol.ADMINISTRADOR:
            qs = qs.filter(creado_por_usuario=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CitaListSerializer
        if self.action == "retrieve":
            return CitaDetailSerializer
        return CitaSerializer

    def perform_create(self, serializer):
        serializer.validated_data["creado_por_usuario"] = self.request.user
        super().perform_create(serializer)
        cita = serializer.instance
        if cita.tipo_cita == Cita.TipoCita.WALK_IN:
            try:
                from apps.acceso.services import registrar_walkin
                registrar_walkin(cita)
            except Exception:  # noqa: BLE001
                pass
        from .services import enviar_notificacion_cita
        enviar_notificacion_cita(cita)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cita = serializer.instance
        from .services import enviar_notificacion_cita
        enviar_notificacion_cita(cita)

    def perform_destroy(self, instance):
        if instance.tipo == Cita.Tipo.PROVEEDOR and EmpleadoCita.objects.filter(cita=instance).exists():
            raise PermissionDenied("La cita de proveedor tiene empleados asignados.")
        if instance.tipo == Cita.Tipo.DIRECTA and instance.asistentes.exists():
            raise PermissionDenied("La cita directa tiene asistentes registrados.")
        super().perform_destroy(instance)

    @action(detail=False, methods=["get"], url_path="buscar-personas")
    def buscar_personas(self, request):
        """Autocomplete unificado: devuelve contactos + empleados activos que coincidan con ?q=."""
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response([])

        results: list[dict] = []

        empleados = (
            Empleado.objects.filter(nombre__icontains=q, estado=Empleado.Estado.ACTIVO)
            .select_related("proveedor")[:10]
        )
        for e in empleados:
            try:
                empresa = e.proveedor.proveedor.nombre if hasattr(e.proveedor, "proveedor") else ""
            except Exception:  # noqa: BLE001
                empresa = ""
            results.append({
                "id": e.id,
                "tipo": AsistenteCita.Tipo.EMPLEADO,
                "nombre": e.nombre,
                "email": e.email or "",
                "telefono": e.telefono or "",
                "empresa": empresa,
                "label": f"Empleado: {e.nombre}" + (f" — {empresa}" if empresa else ""),
            })

        contactos = Contacto.objects.filter(nombre__icontains=q)[:10]
        for c in contactos:
            results.append({
                "id": c.id,
                "tipo": AsistenteCita.Tipo.CONTACTO,
                "nombre": c.nombre,
                "email": c.email or "",
                "telefono": c.telefono or "",
                "empresa": "",
                "label": f"Contacto: {c.nombre}",
            })

        return Response(results)

    @action(detail=True, methods=["get"], url_path="asistentes")
    def asistentes_list(self, request, pk=None):
        """Lista los asistentes registrados para una cita."""
        cita = self.get_object()
        data = AsistenteCitaSerializer(cita.asistentes.all(), many=True).data
        return Response(data)

    @action(detail=True, methods=["post"], url_path="reenviar-invitacion")
    def reenviar_invitacion(self, request, pk=None):
        """Reenvía el correo de invitación (con gafete QR) a todos los asistentes con email."""
        cita = self.get_object()
        if cita.tipo_cita == Cita.TipoCita.WALK_IN:
            return Response(
                {"detail": "Las citas walk-in no envían invitaciones."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .services import enviar_notificacion_cita
        enviados = enviar_notificacion_cita(cita)
        if enviados == 0:
            sin_email = cita.asistentes.filter(email__isnull=True).count() + cita.asistentes.filter(email="").count()
            total = cita.asistentes.count()
            if total == 0:
                return Response({"detail": "Esta cita no tiene invitados registrados."}, status=status.HTTP_400_BAD_REQUEST)
            if sin_email == total:
                return Response({"detail": "Ningún invitado tiene correo registrado."}, status=status.HTTP_400_BAD_REQUEST)
        plural = "correo" if enviados == 1 else "correos"
        return Response({"detail": f"{enviados} {plural} enviado{'s' if enviados != 1 else ''}.", "enviados": enviados})


class AsistenteCitaViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = AsistenteCita.objects.all().order_by("id")
    serializer_class = AsistenteCitaSerializer
    permission_classes = _PERMS
    filterset_fields = ["cita", "tipo", "estado"]

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser], url_path="ocr-ine")
    def ocr_ine(self, request, pk=None):
        """Captura la INE: OCR (Textract/sandbox) → ine_data cifrado + imagen en disco privado."""
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
        asistente.path_ine.save(f"ine_{asistente.id}.jpg", imagen, save=False)
        asistente.ine_capturado = True
        asistente.save()
        return Response({"ine_capturado": True, "datos": datos})
