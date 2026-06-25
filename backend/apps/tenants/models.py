"""Modelos del CONTROL PLANE (schema ``public``).

Aquí viven el tenant y su ciclo comercial (plan, suscripción, créditos, billing), la operación
del super-admin (MFA, mantenimiento, Mesa de Ayuda) y los dispositivos edge con su cola de
comandos. Todo en ``public``: ningún dato operativo de un tenant vive aquí.

Referencias: MODELO_DATOS_SAR §5, PLAYBOOK_SAR_XENTY §5/§9 (F0).
"""
from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

from common.fields import EncryptedCharField


class Tenant(TenantMixin):
    """Cliente del SaaS. Un schema PostgreSQL aislado por tenant (django-tenants).

    Absorbe los campos de suscripción del ``tenants`` origen (company, trial_ends_at,
    subscription_status…) en un único ciclo de vida ``estado``.
    """

    class Estado(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVO = "activo", "Activo"
        SUSPENDIDO = "suspendido", "Suspendido"
        CANCELADO = "cancelado", "Cancelado"

    nombre = models.CharField(max_length=200)  # era `company`
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    # Dunning/retención: el middleware EnforceModoSoloLectura responde 423 cuando está activo.
    modo_solo_lectura = models.BooleanField(default=False)
    plan = models.ForeignKey(
        "tenants.Plan", on_delete=models.SET_NULL, null=True, blank=True, related_name="tenants"
    )
    stripe_customer_id = models.CharField(max_length=64, null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)  # metadatos varios del origen
    created_on = models.DateField(auto_now_add=True)

    # django-tenants: crea el schema al guardar; nunca lo dropea automáticamente (seguridad).
    auto_create_schema = True
    auto_drop_schema = False

    def __str__(self) -> str:
        return f"{self.nombre} ({self.schema_name})"


class Domain(DomainMixin):
    """Subdominio que resuelve al tenant (``<slug>.xenty.mx``). Origen: ``domains``."""


class Plan(models.Model):
    """Plan comercial: precio, módulos habilitados y límites de cuota."""

    nombre = models.CharField(max_length=120)
    clave = models.CharField(max_length=60, unique=True)  # estable para código (no IDs)
    descripcion = models.TextField(null=True, blank=True)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_price_id = models.CharField(max_length=64, null=True, blank=True)
    modulos = models.JSONField(default=list, blank=True)  # claves de módulo activas (RequiereModulo)
    limites = models.JSONField(default=dict, blank=True)  # p. ej. {"usuarios": 10, "eventos": 50}
    activo = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.nombre


class Suscripcion(models.Model):
    """Suscripción Stripe del tenant. Gobierna el estado comercial vía webhooks."""

    class Estado(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVA = "activa", "Activa"
        MOROSA = "morosa", "Morosa"  # dunning
        CANCELADA = "cancelada", "Cancelada"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="suscripciones")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="suscripciones")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.TRIAL)
    stripe_subscription_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    periodo_inicio = models.DateTimeField(null=True, blank=True)
    periodo_fin = models.DateTimeField(null=True, blank=True)
    cancelar_al_fin_periodo = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)


class SaldoCreditos(models.Model):
    """Saldo actual de créditos del tenant (cacheado). La verdad es el ledger (MovimientoCredito)."""

    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="saldo_creditos")
    saldo = models.IntegerField(default=0)
    actualizado = models.DateTimeField(auto_now=True)


class MovimientoCredito(models.Model):
    """Ledger append-only de créditos. Nunca se actualiza ni borra: solo se inserta."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="movimientos_credito")
    delta = models.IntegerField()  # + compra / - consumo
    motivo = models.CharField(max_length=160)
    saldo_resultante = models.IntegerField()
    referencia = models.CharField(max_length=120, null=True, blank=True)  # id externo / nota
    creado = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado"]


class IntentoPago(models.Model):
    """Intento de cobro (suscripción o paquete de créditos)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EXITOSO = "exitoso", "Exitoso"
        FALLIDO = "fallido", "Fallido"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="intentos_pago")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, default="MXN")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    stripe_payment_intent_id = models.CharField(max_length=64, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)


class Factura(models.Model):
    """Factura emitida por Stripe para el tenant."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="facturas")
    stripe_invoice_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fin = models.DateField(null=True, blank=True)
    url_pdf = models.URLField(null=True, blank=True)
    pagada = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)


class SuperAdminManager(BaseUserManager):
    """Manager del super-admin del control plane (autenticatable separado del tenant)."""

    use_in_migrations = True

    def create_user(self, email, nombre, password=None, **extra):
        if not email:
            raise ValueError("El super-admin requiere email.")
        user = self.model(email=self.normalize_email(email), nombre=nombre, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra):
        extra.setdefault("activo", True)
        return self.create_user(email, nombre, password, **extra)


class SuperAdmin(AbstractBaseUser):
    """Operador del control plane (Nivel 1). Auth por JWT propio + MFA; no es AUTH_USER_MODEL.

    Vive en ``public``: gestiona tenants, planes, billing y dispositivos edge. Nunca accede a datos
    operativos de un tenant.
    """

    nombre = models.CharField(max_length=160)
    email = models.EmailField(unique=True)
    activo = models.BooleanField(default=True)
    # MFA del control plane (TOTP + WebAuthn). Secreto TOTP cifrado en reposo.
    mfa_habilitado = models.BooleanField(default=False)
    mfa_totp_secret = EncryptedCharField(max_length=64, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    objects = SuperAdminManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    @property
    def is_active(self) -> bool:  # contrato esperado por los backends de auth
        return self.activo

    def save(self, *args, **kwargs):
        # Singleton: solo puede existir UN super-admin con super permisos.
        if self._state.adding and SuperAdmin.objects.exists():
            raise ValidationError("Ya existe un super-administrador; solo puede haber uno.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email


class Version(models.Model):
    """Registro de versiones desplegadas por componente (auditoría de release)."""

    componente = models.CharField(max_length=60)  # backend, frontend-acceso, edge…
    numero = models.CharField(max_length=40)
    notas = models.TextField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)


class VentanaMantenimiento(models.Model):
    """Ventana de mantenimiento. El middleware EnforceMantenimiento responde 503 mientras está activa."""

    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    mensaje = models.CharField(max_length=255, null=True, blank=True)
    activa = models.BooleanField(default=True)


class ConfiguracionMesa(models.Model):
    """Conexión a Mesa de Ayuda (Nivel B) por tenant. Solo lectura de salud de config."""

    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="config_mesa")
    base_url = models.URLField(null=True, blank=True)
    api_key = EncryptedCharField(max_length=255, null=True, blank=True)
    habilitada = models.BooleanField(default=False)


class DispositivoEdge(models.Model):
    """Raspberry Pi en torniquetes/plumas. Origen: ``devices_tenants`` (BD central)."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="dispositivos")
    mac_address = models.CharField(max_length=32, unique=True)
    nombre = models.CharField(max_length=120)
    # Secreto HMAC cifrado en reposo (REMEDIACION §C3/§7); jamás en claro ni en git.
    token = EncryptedCharField(max_length=255)
    precinct_id = models.BigIntegerField(null=True, blank=True)  # ref lógica dentro del tenant
    access_point_id = models.BigIntegerField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.nombre} [{self.mac_address}]"


class ComandoEdge(models.Model):
    """Cola de comandos para dispositivos (long-poll). Origen: ``edge_commands`` (BD central)."""

    class Tipo(models.TextChoices):
        RELAY_OPEN = "relay.open", "Abrir relé"
        DISPLAY_TEXT = "display.text", "Mostrar texto"

    class Estado(models.TextChoices):
        PENDING = "pending", "Pendiente"
        SENT = "sent", "Enviado"
        ACK = "ack", "Confirmado"

    dispositivo = models.ForeignKey(
        DispositivoEdge, on_delete=models.SET_NULL, null=True, related_name="comandos"
    )
    tipo = models.CharField(max_length=50, choices=Tipo.choices)
    port = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    texto = models.CharField(max_length=255, null=True, blank=True)
    timeout_sec = models.PositiveIntegerField(null=True, blank=True)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDING, db_index=True
    )
    # Anti-replay del long-poll/HMAC (REMEDIACION §7.7 / A1): nonce de un solo uso por dispositivo.
    nonce = models.CharField(max_length=64, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
