"""Mensajería WhatsApp (DATA PLANE): campañas segmentadas y sus destinatarios.

Envío por Celery con reintentos; UltraMsg tras interfaz (credenciales por entorno, REMEDIATION §C2).

Referencia: MODELO_DATOS_SAR §6.10 · SAR_FUNCIONALIDADES §12.
"""

from __future__ import annotations

from django.db import models


class Mensaje(models.Model):  # messages
    class Segmento(models.TextChoices):
        RECINTO = "recinto", "Recinto"
        ZONA = "zona", "Zona"
        EVENTO = "evento", "Evento"
        TODOS_EVENTOS = "todos_eventos", "Todos los eventos"
        TODOS_RECINTOS = "todos_recintos", "Todos los recintos"
        RECINTOS_Y_ZONAS = "recintos_y_zonas", "Recintos y zonas"

    class Estado(models.IntegerChoices):
        PENDIENTE = 0, "Pendiente"
        EN_PROGRESO = 1, "En progreso"
        CANCELADO = 2, "Cancelado"
        COMPLETADO = 3, "Completado"

    cuerpo = models.TextField()
    archivo = models.FileField(upload_to="mensajes/", null=True, blank=True)
    segmento = models.CharField(max_length=20, choices=Segmento.choices, default=Segmento.RECINTO)
    segmento_id = models.BigIntegerField(null=True, blank=True)  # id de recinto/zona/evento
    estado = models.IntegerField(choices=Estado.choices, default=Estado.PENDIENTE)
    progreso = models.FloatField(default=0)
    creado_por = models.ForeignKey("accounts.Usuario", on_delete=models.SET_NULL, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)


class DestinatarioMensaje(models.Model):  # message_recipients
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIADO = "enviado", "Enviado"
        ENTREGADO = "entregado", "Entregado"  # confirmado por el webhook del XCC (delivered)
        LEIDO = "leido", "Leído"  # confirmado por el webhook del XCC (read)
        FALLIDO = "fallido", "Fallido"

    mensaje = models.ForeignKey(Mensaje, on_delete=models.CASCADE, related_name="destinatarios")
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )  # FIX: índice para seguimiento de progreso
    external_id = models.CharField(max_length=64, null=True, blank=True)  # id del proveedor
    proveedor = models.CharField(max_length=20, null=True, blank=True)  # qué proveedor lo envió
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)


class PreferenciaMensajeria(models.Model):
    """Preferencia de proveedores de WhatsApp del tenant (ARQUITECTURA_CONNECTOR §8.2).

    Singleton por tenant (vive en el schema del tenant). Gobierna qué proveedores usa el Router y en
    qué orden. ``proveedores_orden`` es una lista de claves (``"ultramsg"``, ``"xcc"``, ``"sandbox"``);
    el Router filtra a las implementaciones realmente registradas y respeta el master switch global
    del Connector, así que listar ``"xcc"`` sin Connector activo simplemente lo salta (no rompe nada).
    """

    proveedores_orden = models.JSONField(default=list, blank=True)  # ["ultramsg", "xcc"]
    failover_habilitado = models.BooleanField(default=True)
    reintentos = models.PositiveSmallIntegerField(default=1)
    timeout_ms = models.PositiveIntegerField(default=15000)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia de mensajería"

    @classmethod
    def cargar(cls) -> PreferenciaMensajeria:
        """Única fila del tenant (creada con defaults si no existe). Singleton por schema."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton por tenant
        super().save(*args, **kwargs)


class RegistroEnvio(models.Model):
    """Ledger append-only de notificaciones sueltas (ARQUITECTURA_CONNECTOR §9).

    Trazabilidad de qué proveedor atendió cada notificación y su resultado, para failover/auditoría.
    No guarda el teléfono completo (PII): solo una máscara (``****1234``).
    """

    destino_mascara = models.CharField(max_length=24)
    proveedor = models.CharField(max_length=20)
    ok = models.BooleanField(default=False)
    external_id = models.CharField(max_length=64, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado"]
