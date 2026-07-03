"""Acceso físico: escáner (guardia) + bitácora con registro de salida."""
from __future__ import annotations

from django.db import connection
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequierePermisoPersonalizado, RequiereRol

from .detalle import construir_contexto
from .models import RegistroAcceso
from .serializers import RegistroAccesoSerializer
from .services import procesar_escaneo

_SCANNER = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("acceso"),
    RequiereRol("guardia", "administrador", "recepcion", "usuario"),
    RequierePermisoPersonalizado("acceso"),
]
_BITACORA = [
    *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("acceso"),
    RequiereRol("guardia", "administrador", "editor", "recepcion", "usuario"),
    RequierePermisoPersonalizado("acceso"),
]


def _foto_url(request, foto) -> str | None:
    if not foto:
        return None
    return request.build_absolute_uri(foto.url)


def _identidad(request, reg) -> dict:
    """Nombre/empresa/foto del portador del QR, para que el guardia coteje visualmente.

    ``reg`` es ``RegistroAcceso`` (evento/cita/denegado) o ``RegistroAccesoParking`` (parking,
    sin identidad de persona — es un cajón/vehículo).
    """
    if getattr(reg, "empleado_id", None):
        empleado = reg.empleado
        cuenta = empleado.proveedor  # CuentaProveedor
        empresa = cuenta.proveedor.nombre if cuenta and cuenta.proveedor_id else None
        return {"nombre": empleado.nombre, "empresa": empresa, "foto_url": _foto_url(request, empleado.foto)}
    if getattr(reg, "asistente_id", None):
        asistente = reg.asistente
        empresa = asistente.cita.proveedor.nombre if asistente.cita.proveedor_id else None
        foto = None
        persona = asistente.persona  # Contacto o Empleado (GenericForeignKey)
        if persona is not None:
            foto = getattr(persona, "foto", None)
        return {"nombre": asistente.nombre, "empresa": empresa, "foto_url": _foto_url(request, foto)}
    return {"nombre": None, "empresa": None, "foto_url": None}


class EscanearView(APIView):
    """POST /api/acceso/escanear/ {qr, placa?} — valida y registra el acceso."""

    permission_classes = _SCANNER

    def post(self, request):
        reg, permitido, motivo = procesar_escaneo(
            request.data.get("qr", ""), connection.schema_name, placa=request.data.get("placa")
        )
        return Response({
            "permitido": permitido,
            "motivo": motivo,
            "registro_id": reg.id,
            "tipo_acceso": getattr(reg, "tipo_acceso", None),
            **_identidad(request, reg),
            **construir_contexto(request, reg),
        })


class RegistroAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitácora de accesos (solo lectura) + acción de registrar salida."""

    serializer_class = RegistroAccesoSerializer
    permission_classes = _BITACORA
    filterset_fields = ["tipo_acceso", "metodo"]

    def get_queryset(self):
        qs = RegistroAcceso.objects.select_related(
            "empleado", "asistente", "evento", "cita"
        ).order_by("-hora_entrada")
        p = self.request.query_params
        if p.get("fecha_desde"):
            qs = qs.filter(hora_entrada__date__gte=p["fecha_desde"])
        if p.get("fecha_hasta"):
            qs = qs.filter(hora_entrada__date__lte=p["fecha_hasta"])
        return qs

    @action(detail=True, methods=["post"])
    def salida(self, request, pk=None):
        reg = self.get_object()
        reg.hora_salida = timezone.now()
        reg.save(update_fields=["hora_salida"])
        # F7: WhatsApp de confirmación de salida.
        return Response({"hora_salida": reg.hora_salida})

    def get_permissions(self):
        if self.action == "rechazar":
            return [p() for p in _SCANNER]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        """Override del guardia: convierte una entrada recién concedida en denegada.

        Para el caso "el QR es válido pero la persona frente al guardia no coincide con la
        foto" — la única corrección humana permitida sobre el veredicto automático del escáner.
        """
        reg = self.get_object()
        if reg.tipo_acceso != RegistroAcceso.TipoAcceso.ENTRADA or reg.hora_salida is not None:
            return Response(
                {"detail": "Solo se puede rechazar una entrada recién registrada, sin salida."},
                status=status.HTTP_409_CONFLICT,
            )
        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            return Response({"detail": "El motivo es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        reg.tipo_acceso = RegistroAcceso.TipoAcceso.DENEGADO
        reg.observaciones = motivo
        reg.save(update_fields=["tipo_acceso", "observaciones"])
        return Response({"tipo_acceso": reg.tipo_acceso, "observaciones": reg.observaciones})
