"""``CuentaProveedor``: autenticatable del contexto *proveedores* (autoservicio).

Segundo contexto de autenticación del tenant (CLAUDE.md §4): credenciales del panel de proveedor,
flujo JWT propio (claim ``ctx="proveedores"``). NO es ``AUTH_USER_MODEL`` ni se colapsa con
``Usuario``. El catálogo ``Proveedor`` (empresa/Supplier) y la FK ``proveedor`` se implementan en F1.

Referencia: MODELO_DATOS_SAR §6.2.
"""

from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from common.fields import EncryptedCharField


class Proveedor(models.Model):  # suppliers (empresa externa)
    """Empresa proveedora. Su responsable es una ``CuentaProveedor``. RFC validado al guardar."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADO = "confirmado", "Confirmado"
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    nombre = models.CharField(max_length=200)
    razon_social = models.CharField(max_length=255, null=True, blank=True)
    rfc = models.CharField(max_length=13, null=True, blank=True, db_index=True)
    email = models.EmailField(null=True, blank=True)
    email_responsable = models.EmailField(null=True, blank=True)
    nombre_responsable = models.CharField(max_length=200, null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    file_repse = models.FileField(upload_to="proveedores/repse/", null=True, blank=True)
    file_sua = models.FileField(upload_to="proveedores/sua/", null=True, blank=True)
    responsable = models.ForeignKey(
        "proveedores.CuentaProveedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proveedor_responsable",
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre


class CuentaProveedorManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, nombre, password=None, **extra):
        if not email:
            raise ValueError("La cuenta de proveedor requiere email.")
        cuenta = self.model(email=self.normalize_email(email), nombre=nombre, **extra)
        cuenta.set_password(password)
        cuenta.save(using=self._db)
        return cuenta


class CuentaProveedor(AbstractBaseUser):
    """Usuario del panel proveedor (Nivel 3). Solo ve los datos de su empresa."""

    class Rol(models.TextChoices):
        ADMIN = "admin", "Admin"
        USUARIO = "usuario", "Usuario"

    nombre = models.CharField(max_length=160)
    apellidos = models.CharField(max_length=160, null=True, blank=True)
    email = models.EmailField(unique=True)
    email_verificado = models.DateTimeField(null=True, blank=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.USUARIO)
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.CASCADE, null=True, blank=True, related_name="cuentas"
    )  # era company_id en el origen
    puesto = models.CharField(max_length=120, null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    activo = models.BooleanField(default=True)
    # MFA (TOTP). Secreto cifrado en reposo (Fernet).
    mfa_habilitado = models.BooleanField(default=False)
    mfa_totp_secret = EncryptedCharField(max_length=64, null=True, blank=True)
    # PII cifrada en reposo (Fernet):
    curp = EncryptedCharField(max_length=18, null=True, blank=True)
    nss = EncryptedCharField(max_length=11, null=True, blank=True)
    file_ine = models.FileField(
        upload_to="proveedores/ine/", null=True, blank=True
    )  # disco PRIVADO
    foto = models.ImageField(upload_to="proveedores/fotos/", null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    objects = CuentaProveedorManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    @property
    def is_active(self) -> bool:
        return self.activo

    def __str__(self) -> str:
        return self.email
