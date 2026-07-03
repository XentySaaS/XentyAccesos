"""Endpoints de cumplimiento 69-B: validar proveedor, consultar EFOS y resultados."""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.efos.models import SatEfo
from apps.proveedores.models import Proveedor
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import ResultadoLista69b
from .serializers import ResultadoLista69bSerializer, SatEfoSerializer
from .services import revalidar_todos, validar_69b

_PERMS = [
    *PERMISOS_BASE(),
    ContextoAcceso,
    RequiereModulo("cumplimiento"),
    RequiereRol("administrador"),
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


class RevalidarView(APIView):
    """POST /api/cumplimiento/revalidar/ — revalida a todos los proveedores contra el padrón."""

    permission_classes = _PERMS

    def post(self, request):
        return Response(revalidar_todos())


class ResumenView(APIView):
    """GET /api/cumplimiento/resumen/ — estado del padrón y proveedores marcados (alerta al tenant)."""

    permission_classes = _PERMS

    def get(self, request):
        from django.db.models import Max, OuterRef, Subquery

        total_efos = SatEfo.objects.count()
        ultima = SatEfo.objects.aggregate(f=Max("actualizado"))["f"]

        # Auto-reparación: si el padrón está vacío, dispara la importación en background una sola
        # vez (guard en caché por schema) para no depender de que el admin haga nada manual.
        importando = False
        if total_efos == 0:
            from django.core.cache import cache
            from django.db import connection

            lock = f"efos_import_pendiente:{connection.schema_name}"
            if cache.add(lock, "1", timeout=3600):
                from .tasks import importar_efos_task

                try:
                    importar_efos_task.delay(connection.schema_name)
                except Exception:  # noqa: BLE001 — sin broker (dev): no romper la respuesta.
                    cache.delete(lock)
            importando = True

        # Último resultado por proveedor; marcamos los que quedaron ENCONTRADO.
        ultimos = ResultadoLista69b.objects.filter(proveedor=OuterRef("pk")).order_by("-creado")
        marcados = Proveedor.objects.annotate(
            ult_estado=Subquery(ultimos.values("estado")[:1]),
            ult_rfc=Subquery(ultimos.values("rfc")[:1]),
        ).filter(ult_estado=ResultadoLista69b.Estado.ENCONTRADO)
        sat = {
            e.rfc: e.situacion for e in SatEfo.objects.filter(rfc__in=[p.ult_rfc for p in marcados])
        }
        proveedores = [
            {
                "id": p.id,
                "nombre": p.nombre,
                "rfc": p.ult_rfc,
                "situacion": sat.get(p.ult_rfc),
                "estado": p.estado,
            }
            for p in marcados
        ]
        return Response(
            {
                "total_efos": total_efos,
                "ultima_actualizacion": ultima,
                "padron_cargado": total_efos > 0,
                "importando": importando,
                "marcados": len(proveedores),
                "proveedores": proveedores,
            }
        )


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
