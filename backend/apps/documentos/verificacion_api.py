"""Endpoints agregados para el workspace de verificación documental (drill-down proveedor → empleado).

Para verificadores/administradores del contexto *acceso*. Devuelven **conteos agregados** (no listas
planas de documentos) para que la pantalla escale a mucho volumen: primero los proveedores con
documentos por revisar, luego los empleados del proveedor; el nivel de documentos reusa el endpoint
existente ``documentos-empleado/?empleado=&estado=``. Dimensiones comunes: ``estado`` (0/1/2),
``evento`` y ``mis_eventos`` (solo los eventos que el usuario verifica).
"""

from __future__ import annotations

from django.db.models import Count, F, Max
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import DocumentoEmpleado

_VERIF_PERMS = [
    *PERMISOS_BASE(),
    ContextoAcceso,
    RequiereModulo("documentos"),
    RequiereRol("verificador", "administrador"),
]


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _verdadero(v) -> bool:
    return str(v).lower() in ("1", "true", "si", "sí")


def _aplicar_orden(rows, orden: str | None, campo_nombre: str):
    """Ordena las filas agregadas: pendientes (default) / recientes / antiguos / A-Z / Z-A.

    ``ultimo`` = fecha del documento más reciente del grupo (para ordenar por recencia).
    """
    if orden == "recientes":
        return rows.order_by("-ultimo")
    if orden == "antiguos":
        return rows.order_by("ultimo")
    if orden == "az":
        return rows.order_by(campo_nombre)
    if orden == "za":
        return rows.order_by(f"-{campo_nombre}")
    return rows.order_by("-docs", campo_nombre)  # "pendientes" (default): más por revisar primero


def _base_qs(request):
    """``DocumentoEmpleado`` filtrado por las dimensiones comunes (estado, evento, mis_eventos)."""
    qs = DocumentoEmpleado.objects.all()
    estado = _int(request.query_params.get("estado"))
    if estado is not None:
        qs = qs.filter(estado=estado)
    evento = _int(request.query_params.get("evento"))
    if evento is not None:
        qs = qs.filter(empleado__empleadoeventoproveedor__evento_proveedor__evento_id=evento)
    if _verdadero(request.query_params.get("mis_eventos")):
        qs = qs.filter(
            empleado__empleadoeventoproveedor__evento_proveedor__evento__verificadores=request.user
        )
    return qs


class ProveedoresVerificacionView(APIView):
    """GET — proveedores (empresas) con documentos en el estado dado + conteos. Paginado."""

    permission_classes = _VERIF_PERMS

    def get(self, request):
        qs = _base_qs(request)
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(empleado__proveedor__proveedor__nombre__icontains=search)
        rows = qs.values(
            proveedor_id=F("empleado__proveedor__proveedor_id"),
            proveedor_nombre=F("empleado__proveedor__proveedor__nombre"),
        ).annotate(
            docs=Count("id", distinct=True),
            empleados=Count("empleado", distinct=True),
            ultimo=Max("creado"),
        )
        rows = _aplicar_orden(rows, request.query_params.get("orden"), "proveedor_nombre")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(list(page))


class EmpleadosVerificacionView(APIView):
    """GET — empleados del ``proveedor`` con documentos en el estado dado + conteo. Paginado."""

    permission_classes = _VERIF_PERMS

    def get(self, request):
        proveedor = _int(request.query_params.get("proveedor"))
        if proveedor is None:
            return Response({"detail": "Falta el parámetro 'proveedor'."}, status=400)
        qs = _base_qs(request).filter(empleado__proveedor__proveedor_id=proveedor)
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(empleado__nombre__icontains=search)
        rows = qs.values(emp_id=F("empleado_id"), emp_nombre=F("empleado__nombre")).annotate(
            docs=Count("id", distinct=True), ultimo=Max("creado")
        )
        rows = _aplicar_orden(rows, request.query_params.get("orden"), "emp_nombre")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(list(page))


class EventosVerificacionView(APIView):
    """GET — lista breve de eventos para el filtro (id, nombre). ``mis_eventos`` = los que yo verifico."""

    permission_classes = _VERIF_PERMS

    def get(self, request):
        from apps.eventos.models import Evento

        qs = Evento.objects.all()
        if _verdadero(request.query_params.get("mis_eventos")):
            qs = qs.filter(verificadores=request.user)
        eventos = list(qs.order_by("-vigencia_inicio").values("id", "nombre")[:200])
        return Response({"eventos": eventos})
