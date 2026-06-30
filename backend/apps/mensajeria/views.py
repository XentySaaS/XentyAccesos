"""ViewSet de campañas: crea, segmenta y dispara el envío por Celery."""
from __future__ import annotations

from django.db import connection
from rest_framework import viewsets

from apps.config.services import AuditViewSetMixin
from common.permissions import PERMISOS_BASE, ContextoAcceso, RequiereModulo, RequiereRol

from .models import Mensaje
from .serializers import MensajeSerializer
from .services import crear_destinatarios
from .tasks import enviar_campana


class MensajeViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Mensaje.objects.all().order_by("-creado")
    serializer_class = MensajeSerializer
    permission_classes = [
        *PERMISOS_BASE(), ContextoAcceso, RequiereModulo("mensajeria"),
        RequiereRol("administrador", "editor"),
    ]
    filterset_fields = ["estado", "segmento"]

    def perform_create(self, serializer):
        serializer.validated_data["creado_por"] = self.request.user
        super().perform_create(serializer)
        mensaje = serializer.instance
        crear_destinatarios(mensaje)
        # Envío asíncrono por Celery, dentro del contexto del tenant.
        enviar_campana.delay(connection.schema_name, mensaje.id)
