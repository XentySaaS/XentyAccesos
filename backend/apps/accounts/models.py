"""Modelo de identidad del DATA PLANE: ``Usuario`` (contexto operación, schema por tenant).

Es el ``AUTH_USER_MODEL`` del proyecto. El proveedor (``apps.proveedores.CuentaProveedor``) y el
super-admin (``apps.tenants.SuperAdmin``) son autenticatables SEPARADOS con su propio flujo JWT
(CLAUDE.md §4 / PLAYBOOK §2.4): no se colapsan en este modelo.

Referencia: MODELO_DATOS_SAR §6.1.
"""
from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from common.fields import EncryptedCharField


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, nombre, password=None, **extra):
        if not email:
            raise ValueError("El usuario requiere email.")
        user = self.model(email=self.normalize_email(email), nombre=nombre, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra):
        extra.setdefault("rol", Usuario.Rol.ADMINISTRADOR)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("activo", True)
        if extra["is_staff"] is not True or extra["is_superuser"] is not True:
            raise ValueError("El superusuario debe tener is_staff e is_superuser en True.")
        return self.create_user(email, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Operador del recinto (Nivel 2). Login exige ``activo=True``; la baja congela, no elimina."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        EDITOR = "editor", "Editor"
        GUARDIA = "guardia", "Guardia"  # Security Guard
        GERENTE = "gerente", "Gerente"  # Manager
        RECEPCION = "recepcion", "Recepcionista"  # Receptionist
        USUARIO = "usuario", "Usuario"
        VERIFICADOR = "verificador", "Verificador"  # Verifier

    nombre = models.CharField(max_length=160)
    email = models.EmailField(unique=True)
    email_verificado = models.DateTimeField(null=True, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.EDITOR)
    recinto = models.ForeignKey(
        "recintos.Recinto", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="usuarios",
    )
    telefono = models.CharField(max_length=30, null=True, blank=True)
    activo = models.BooleanField(default=True)  # reemplaza status=inactive; el login lo exige
    fecha_baja = models.DateTimeField(null=True, blank=True)  # baja lógica (low_login/delete_at)
    is_staff = models.BooleanField(default=False)  # acceso al admin de Django del tenant
    # MFA (TOTP). Secreto cifrado en reposo (Fernet). WebAuthn se añade aparte.
    mfa_habilitado = models.BooleanField(default=False)
    mfa_totp_secret = EncryptedCharField(max_length=64, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    @property
    def is_active(self) -> bool:
        return self.activo

    def __str__(self) -> str:
        return self.email
