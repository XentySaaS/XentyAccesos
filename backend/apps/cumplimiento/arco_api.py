"""Endpoints ARCO / LFPDPPP (rol administrador) + aviso de privacidad (edición admin y lectura pública).

Privacidad es una obligación legal, no una función de plan: por eso NO se gatea con
``RequiereModulo``. El export entrega PII descifrada del titular del propio tenant (aislamiento =
policy de pertenencia). Toda acción sensible queda en ``HistorialCambio``.
"""

from __future__ import annotations

from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereRol

from . import arco
from .models import DocumentoLegal, SolicitudArco, TitularTipo

_PERMS_ADMIN = [*PERMISOS_BASE(), ContextoAcceso, RequiereRol("administrador")]

# Plazo legal de respuesta a una solicitud ARCO (LFPDPPP art. 32: 20 días naturales).
DIAS_PLAZO = 20


def _log(request, descripcion: str, modelo: str, modelo_id: int, accion: str) -> None:
    from apps.config.models import HistorialCambio

    try:
        HistorialCambio.objects.create(
            descripcion=descripcion,
            modelo=modelo,
            modelo_id=modelo_id,
            usuario=getattr(request, "user", None) if request.user.is_authenticated else None,
            accion=accion,
        )
    except Exception:  # noqa: BLE001 — la auditoría nunca debe tumbar la acción
        pass


def _tipo_valido(tipo: str) -> bool:
    return tipo in TitularTipo.values


# ── Búsqueda de titulares ────────────────────────────────────────────────────
class BuscarTitularesView(APIView):
    """GET /api/cumplimiento/arco/titulares/?q= — ubica al solicitante entre los titulares."""

    permission_classes = _PERMS_ADMIN

    def get(self, request):
        return Response({"resultados": arco.buscar_titulares(request.query_params.get("q", ""))})


# ── Acceso / portabilidad ────────────────────────────────────────────────────
class ExportTitularView(APIView):
    """GET /api/cumplimiento/arco/export/<tipo>/<id>/ — descarga JSON con la PII del titular."""

    permission_classes = _PERMS_ADMIN

    def get(self, request, tipo, titular_id):
        if not _tipo_valido(tipo):
            return Response({"detail": "Tipo de titular inválido."}, status=400)
        data = arco.exportar_titular(tipo, titular_id)
        if data is None:
            return Response({"detail": "Titular no encontrado."}, status=404)
        _log(request, f"Export ARCO de {tipo}#{titular_id}", "arco.export", titular_id, "visto")
        resp = JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 2})
        resp["Content-Disposition"] = f'attachment; filename="arco_{tipo}_{titular_id}.json"'
        return resp


# ── Cancelación (anonimización) ──────────────────────────────────────────────
class CancelarTitularView(APIView):
    """POST /api/cumplimiento/arco/cancelar/<tipo>/<id>/ — anonimiza al titular (irreversible)."""

    permission_classes = _PERMS_ADMIN

    def post(self, request, tipo, titular_id):
        if not _tipo_valido(tipo):
            return Response({"detail": "Tipo de titular inválido."}, status=400)
        titular = arco.obtener_titular(tipo, titular_id)
        if titular is None:
            return Response({"detail": "Titular no encontrado."}, status=404)
        desc = arco.mascara_nombre(getattr(titular, "nombre", ""))
        resultado = arco.cancelar_titular(tipo, titular_id)
        # Deja constancia de la solicitud atendida (art. 32) sin PII en claro.
        SolicitudArco.objects.create(
            tipo=SolicitudArco.Tipo.CANCELACION,
            titular_tipo=tipo,
            titular_id=titular_id,
            titular_desc=desc,
            estado=SolicitudArco.Estado.COMPLETADA,
            motivo=(request.data or {}).get("motivo") or None,
            solicitado_por=request.user if request.user.is_authenticated else None,
            plazo_limite=timezone.now().date() + timedelta(days=DIAS_PLAZO),
            resuelto=timezone.now(),
        )
        _log(
            request,
            f"Cancelación ARCO de {tipo}#{titular_id}",
            "arco.cancelacion",
            titular_id,
            "eliminado",
        )
        return Response(resultado)


# ── Solicitudes ARCO (registro y seguimiento) ────────────────────────────────
class SolicitudArcoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudArco
        fields = [
            "id",
            "tipo",
            "titular_tipo",
            "titular_id",
            "titular_desc",
            "estado",
            "motivo",
            "plazo_limite",
            "resuelto",
            "creado",
        ]
        read_only_fields = ["titular_desc", "plazo_limite", "resuelto", "creado"]


class SolicitudArcoViewSet(viewsets.ModelViewSet):
    """CRUD de solicitudes ARCO. Al crear fija el plazo legal y una descripción sin PII."""

    queryset = SolicitudArco.objects.all()
    serializer_class = SolicitudArcoSerializer
    permission_classes = _PERMS_ADMIN
    filterset_fields = ["tipo", "estado", "titular_tipo"]

    def perform_create(self, serializer):
        titular = arco.obtener_titular(
            serializer.validated_data["titular_tipo"], serializer.validated_data["titular_id"]
        )
        serializer.save(
            titular_desc=arco.mascara_nombre(getattr(titular, "nombre", "")),
            plazo_limite=timezone.now().date() + timedelta(days=DIAS_PLAZO),
            solicitado_por=self.request.user if self.request.user.is_authenticated else None,
        )

    def perform_update(self, serializer):
        # Al pasar a un estado final se sella la fecha de resolución.
        estado = serializer.validated_data.get("estado")
        if estado in (SolicitudArco.Estado.COMPLETADA, SolicitudArco.Estado.RECHAZADA):
            serializer.save(resuelto=timezone.now())
        else:
            serializer.save()


# ── Documentos legales (aviso de privacidad, términos y condiciones) ─────────
class DocumentoLegalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoLegal
        fields = ["tipo", "texto", "version", "vigente_desde"]
        read_only_fields = ["tipo", "version", "vigente_desde"]


def documento_vigente(tipo: str):
    """Versión vigente (más alta) de un tipo de documento legal, o ``None``."""
    return DocumentoLegal.objects.filter(tipo=tipo).order_by("-version").first()


def _doc_tipo_valido(tipo: str) -> bool:
    return tipo in DocumentoLegal.Tipo.values


class DocumentoLegalAdminView(APIView):
    """GET/PUT /api/cumplimiento/arco/documentos/<tipo>/ — el admin lee y publica versiones."""

    permission_classes = _PERMS_ADMIN

    def get(self, request, tipo):
        if not _doc_tipo_valido(tipo):
            return Response({"detail": "Tipo de documento inválido."}, status=400)
        doc = documento_vigente(tipo)
        if doc is None:
            return Response({"tipo": tipo, "texto": "", "version": 0, "vigente_desde": None})
        return Response(DocumentoLegalSerializer(doc).data)

    def put(self, request, tipo):
        if not _doc_tipo_valido(tipo):
            return Response({"detail": "Tipo de documento inválido."}, status=400)
        texto = (request.data or {}).get("texto", "").strip()
        if not texto:
            return Response({"detail": "El texto no puede estar vacío."}, status=422)
        actual = documento_vigente(tipo)
        nuevo = DocumentoLegal.objects.create(
            tipo=tipo,
            texto=texto,
            version=(actual.version + 1) if actual else 1,
            actualizado_por=request.user if request.user.is_authenticated else None,
        )
        etiqueta = DocumentoLegal.Tipo(tipo).label
        _log(request, f"{etiqueta} v{nuevo.version}", "DocumentoLegal", nuevo.id, "actualizado")
        return Response(DocumentoLegalSerializer(nuevo).data)


class DocumentoLegalPublicoView(APIView):
    """GET /api/privacidad/documento/<tipo>/ — documento vigente para mostrar públicamente."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request, tipo):
        if not _doc_tipo_valido(tipo):
            return Response({"detail": "Tipo de documento inválido."}, status=400)
        doc = documento_vigente(tipo)
        if doc is None:
            return Response({"detail": "Documento no publicado."}, status=404)
        return Response(DocumentoLegalSerializer(doc).data)
