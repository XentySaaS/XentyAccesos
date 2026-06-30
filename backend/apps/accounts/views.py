"""ViewSets de gestión de usuarios del tenant (solo administradores)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.config.models import HistorialCambio
from apps.config.services import AuditViewSetMixin, registrar as _registrar
from common.permissions import PERMISOS_BASE, RequiereRol

from .models import Usuario
from .serializers import UsuarioCreateSerializer, UsuarioListSerializer, UsuarioUpdateSerializer

_PERMS_ADMIN = [*PERMISOS_BASE(), RequiereRol("administrador")]


class UsuarioViewSet(AuditViewSetMixin, ModelViewSet):
    """CRUD de usuarios del tenant (solo rol administrador)."""

    queryset = Usuario.objects.select_related("recinto").order_by("nombre")
    permission_classes = _PERMS_ADMIN
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        if self.action in ("update", "partial_update"):
            return UsuarioUpdateSerializer
        return UsuarioListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        _registrar(
            f"Creó Usuario «{usuario}»",
            usuario=request.user,
            accion=HistorialCambio.Accion.CREADO,
            modelo="Usuario",
            modelo_id=usuario.pk,
        )
        response_data = UsuarioListSerializer(usuario).data
        # Incluye el password generado una sola vez en la respuesta de creación.
        if hasattr(usuario, "_password_plain"):
            response_data["password_temporal"] = usuario._password_plain
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="resetear-password")
    def resetear_password(self, request, pk=None):
        """Genera una contraseña aleatoria nueva para el usuario."""
        import secrets

        usuario = self.get_object()
        nueva = secrets.token_urlsafe(12)
        usuario.set_password(nueva)
        usuario.save(update_fields=["password"])
        return Response({"password_temporal": nueva})
