"""ViewSet de Empleado (contexto proveedores) + import por Excel idempotente."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.config.services import AuditViewSetMixin
from common.permissions import PERMISOS_BASE, ContextoProveedores, RequiereModulo
from common.validators import validar_archivo

from .models import Empleado
from .serializers import EmpleadoSerializer


class EmpleadoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmpleadoSerializer
    permission_classes = [*PERMISOS_BASE(), ContextoProveedores, RequiereModulo("empleados")]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ["estado"]

    def get_queryset(self):
        actor = self.request.user
        qs = Empleado.objects.all().order_by("id")
        # El proveedor solo ve los empleados de SU empresa (todas las cuentas del mismo Proveedor).
        if getattr(actor, "proveedor_id", None):
            return qs.filter(proveedor__proveedor_id=actor.proveedor_id)
        return qs.filter(proveedor=actor)

    def perform_create(self, serializer):
        serializer.validated_data["proveedor"] = self.request.user
        super().perform_create(serializer)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def importar(self, request):
        """Importa empleados desde un .xlsx (columnas: nombre, email, telefono). Idempotente por email."""
        archivo = request.FILES.get("archivo")
        if not archivo:
            return Response({"detail": "Falta 'archivo' (.xlsx)."}, status=status.HTTP_400_BAD_REQUEST)
        validar_archivo(archivo, extensiones=(".xlsx",), max_mb=5)

        from openpyxl import load_workbook

        ws = load_workbook(archivo, read_only=True, data_only=True).active
        creados = actualizados = 0
        for fila in ws.iter_rows(min_row=2, values_only=True):
            if not fila or not fila[0]:
                continue
            nombre = str(fila[0]).strip()
            email = str(fila[1]).strip().lower() if len(fila) > 1 and fila[1] else None
            telefono = str(fila[2]).strip() if len(fila) > 2 and fila[2] else None
            _, creado = Empleado.objects.update_or_create(
                proveedor=request.user, email=email,
                defaults={"nombre": nombre, "telefono": telefono},
            )
            creados += int(creado)
            actualizados += int(not creado)
        return Response({"creados": creados, "actualizados": actualizados})
