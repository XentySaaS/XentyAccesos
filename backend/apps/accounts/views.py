"""ViewSets de gestión de usuarios del tenant (solo administradores)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.config.models import HistorialCambio
from apps.config.services import AuditViewSetMixin, registrar as _registrar
from common.permissions import PERMISOS_BASE, RequiereRol

from .models import PermisoUsuario, Usuario
from .serializers import (
    PermisoUsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioListSerializer,
    UsuarioUpdateSerializer,
)

_PERMS_ADMIN = [*PERMISOS_BASE(), RequiereRol("administrador")]


class UsuarioViewSet(AuditViewSetMixin, ModelViewSet):
    """CRUD de usuarios del tenant (solo rol administrador)."""

    queryset = Usuario.objects.select_related("recinto").order_by("nombre")
    permission_classes = _PERMS_ADMIN
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

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

    @action(detail=True, methods=["get", "put"], url_path="permisos")
    def permisos(self, request, pk=None):
        """GET → matriz completa (todos los módulos). PUT → reemplaza la lista entera."""
        usuario = self.get_object()
        modulos_todos = [m.value for m in PermisoUsuario.Modulo]

        if request.method == "GET":
            existentes = {p.modulo: p for p in PermisoUsuario.objects.filter(usuario=usuario)}
            resultado = []
            for m in modulos_todos:
                p = existentes.get(m)
                resultado.append({
                    "modulo": m,
                    "modulo_display": PermisoUsuario.Modulo(m).label,
                    "ver":     p.ver     if p else False,
                    "crear":   p.crear   if p else False,
                    "editar":  p.editar  if p else False,
                    "eliminar": p.eliminar if p else False,
                })
            return Response(resultado)

        # PUT: reemplaza toda la lista de permisos
        data = request.data if isinstance(request.data, list) else []
        PermisoUsuario.objects.filter(usuario=usuario).delete()
        creados = []
        for item in data:
            s = PermisoUsuarioSerializer(data=item)
            s.is_valid(raise_exception=True)
            p = s.save(usuario=usuario)
            creados.append(PermisoUsuarioSerializer(p).data)
        _registrar(
            f"Actualizó permisos de Usuario «{usuario}»",
            usuario=request.user,
            accion=HistorialCambio.Accion.ACTUALIZADO,
            modelo="PermisoUsuario",
            modelo_id=usuario.pk,
        )
        return Response(creados)

    @action(detail=True, methods=["post"], url_path="resetear-password")
    def resetear_password(self, request, pk=None):
        """Genera una contraseña aleatoria nueva para el usuario."""
        import secrets

        usuario = self.get_object()
        nueva = secrets.token_urlsafe(12)
        usuario.set_password(nueva)
        usuario.save(update_fields=["password"])
        return Response({"password_temporal": nueva})
