"""Configuración key-value y auditoría append-only (DATA PLANE).

Referencia: MODELO_DATOS_SAR §6.12 · SAR_FUNCIONALIDADES §14.2/14.3.
"""

from __future__ import annotations

from django.db import models


class Opcion(models.Model):  # options (helper get_option del origen)
    clave = models.CharField(max_length=120, unique=True, db_index=True)
    valor = models.TextField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.clave


class HistorialCambio(models.Model):  # change_histories (Change_history)
    class Accion(models.TextChoices):
        CREADO = "creado", "Creado"
        ACTUALIZADO = "actualizado", "Actualizado"
        ELIMINADO = "eliminado", "Eliminado"
        RESTAURADO = "restaurado", "Restaurado"
        ASIGNADO = "asignado", "Asignado"
        DESASIGNADO = "desasignado", "Desasignado"
        VISTO = "visto", "Visto"
        LISTADO = "listado", "Listado"

    descripcion = models.TextField()
    modelo = models.CharField(max_length=120, null=True, blank=True)
    modelo_id = models.BigIntegerField(null=True, blank=True)
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True, db_index=True
    )
    accion = models.CharField(max_length=12, choices=Accion.choices, default=Accion.CREADO)
    # Decisión abierta del modelo: diff antes/después (listo pero opcional).
    antes = models.JSONField(null=True, blank=True)
    despues = models.JSONField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["modelo", "modelo_id"])]
        ordering = ["-creado"]


class BitacoraAcceso(models.Model):  # bitácora de accesos AL SISTEMA (autenticación)
    """Auditoría de autenticación del tenant: quién entró/salió, cuándo, desde dónde y con qué.

    Es distinta de ``HistorialCambio`` (audita **cambios de datos**) y de ``acceso.RegistroAcceso``
    (accesos **físicos** al recinto). Cubre los dos contextos autenticables del tenant (``Usuario``
    de *acceso* y ``CuentaProveedor`` de *proveedores*). El actor se denormaliza (``actor_email`` /
    ``actor_nombre``) para conservar el rastro aunque la cuenta se elimine o el intento sea de un
    correo inexistente. La IP y el dispositivo se guardan **en esta tabla de auditoría** (no en logs
    de aplicación), como excepción acotada a la regla "sin PII en logs".
    """

    class Evento(models.TextChoices):
        LOGIN = "login", "Inicio de sesión"
        LOGIN_FALLIDO = "login_fallido", "Intento fallido"
        LOGOUT = "logout", "Cierre de sesión"

    class Contexto(models.TextChoices):
        ACCESO = "acceso", "Operación"
        PROVEEDORES = "proveedores", "Proveedores"

    evento = models.CharField(max_length=16, choices=Evento.choices, db_index=True)
    contexto = models.CharField(max_length=12, choices=Contexto.choices, db_index=True)
    # FK solo cuando el actor es un Usuario (contexto acceso). Proveedores/intentos anónimos → null,
    # pero el correo queda en actor_email.
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True, db_index=True
    )
    actor_email = models.CharField(max_length=254, db_index=True)
    actor_nombre = models.CharField(max_length=180, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    dispositivo = models.CharField(max_length=180, blank=True, default="")  # resumen legible del UA
    user_agent = models.TextField(
        blank=True, default=""
    )  # UA completo (forense; no se expone en API)
    exito = models.BooleanField(default=True)
    detalle = models.CharField(max_length=200, blank=True, default="")  # motivo del fallo, etc.
    creado = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["contexto", "evento"]),
            models.Index(fields=["actor_email", "creado"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_evento_display()} · {self.actor_email} · {self.creado:%Y-%m-%d %H:%M}"
