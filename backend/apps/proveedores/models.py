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
    # NOTA: FK `proveedor` -> proveedores.Proveedor se añade en F1 (catálogo de empresas).
    puesto = models.CharField(max_length=120, null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    activo = models.BooleanField(default=True)
    # MFA (TOTP). Secreto cifrado en reposo (Fernet).
    mfa_habilitado = models.BooleanField(default=False)
    mfa_totp_secret = EncryptedCharField(max_length=64, null=True, blank=True)
    # PII cifrada en reposo (Fernet):
    curp = EncryptedCharField(max_length=18, null=True, blank=True)
    nss = EncryptedCharField(max_length=11, null=True, blank=True)
    file_ine = models.FileField(upload_to="proveedores/ine/", null=True, blank=True)  # disco PRIVADO
    foto = models.ImageField(upload_to="proveedores/fotos/", null=True, blank=True)

    objects = CuentaProveedorManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    @property
    def is_active(self) -> bool:
        return self.activo

    def __str__(self) -> str:
        return self.email
