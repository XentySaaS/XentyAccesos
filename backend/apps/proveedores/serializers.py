"""Serializers de proveedores (catálogo + onboarding)."""
from __future__ import annotations

import re

from rest_framework import serializers

from common.validators import rfc_valido, validar_archivo

from .models import CuentaProveedor, Proveedor

_DOCS  = (".pdf", ".jpg", ".jpeg", ".png")
_FOTOS = (".jpg", ".jpeg", ".png")

_CURP_RE = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[012])(0[1-9]|[12]\d|3[01])"
    r"[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$",
    re.IGNORECASE,
)


class ProveedorSerializer(serializers.ModelSerializer):
    # RFC obligatorio: se valida estructura + lista 69-B del SAT antes de dar de alta.
    rfc = serializers.CharField(max_length=13)
    # El correo del responsable se usa para crear su cuenta de acceso: debe ser único.
    email_responsable = serializers.EmailField()

    class Meta:
        model = Proveedor
        fields = [
            "id", "nombre", "razon_social", "rfc", "email", "email_responsable",
            "nombre_responsable", "telefono", "direccion", "file_repse", "file_sua",
            "responsable", "estado",
        ]
        read_only_fields = ["estado"]

    def validate_rfc(self, rfc):
        rfc = (rfc or "").upper().strip()
        if not rfc:
            raise serializers.ValidationError("El RFC es obligatorio.")
        if not rfc_valido(rfc):
            raise serializers.ValidationError("RFC inválido (estructura o dígito verificador).")
        # Lista 69-B (SAT): no se permite dar de alta un RFC marcado como EFOS bloqueante.
        from apps.cumplimiento.services import situacion_bloqueante
        from apps.efos.models import SatEfo
        efo = SatEfo.objects.filter(rfc=rfc).first()
        if efo and situacion_bloqueante(efo.situacion):
            raise serializers.ValidationError(
                f"El RFC aparece en la lista 69-B del SAT (situación: {efo.situacion}). No se puede dar de alta."
            )
        return rfc

    def validate_email_responsable(self, email):
        email = (email or "").lower().strip()
        if not email:
            raise serializers.ValidationError("El correo del responsable es obligatorio.")
        otros = Proveedor.objects.filter(email_responsable__iexact=email)
        if self.instance:
            otros = otros.exclude(pk=self.instance.pk)
        if otros.exists():
            raise serializers.ValidationError("Ya existe un proveedor con ese correo de responsable.")
        if CuentaProveedor.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Ese correo ya tiene una cuenta de proveedor registrada.")
        return email

    def validate_file_repse(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=5)
        return f

    def validate_file_sua(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=5)
        return f


class OnboardingProveedorSerializer(serializers.Serializer):
    """Alta de la cuenta del proveedor a partir de una invitación firmada.

    Recibe ``multipart/form-data`` con todos los pasos del wizard en un solo POST.
    """

    # ── Autenticación de la invitación ──────────────────────────────────────
    token = serializers.CharField()

    # ── Paso 1: Empresa ─────────────────────────────────────────────────────
    email_empresa    = serializers.EmailField(required=False, allow_blank=True)
    telefono_empresa = serializers.CharField(max_length=30, required=False, allow_blank=True)
    repse            = serializers.FileField(required=False, allow_null=True)
    sua              = serializers.FileField(required=False, allow_null=True)

    # ── Paso 2: Responsable ─────────────────────────────────────────────────
    nombre    = serializers.CharField(max_length=160)
    apellidos = serializers.CharField(max_length=160, required=False, allow_blank=True)
    puesto    = serializers.CharField(max_length=120, required=False, allow_blank=True)
    email     = serializers.EmailField()              # login de CuentaProveedor
    curp      = serializers.CharField(max_length=18,  required=False, allow_blank=True)
    nss       = serializers.CharField(max_length=11,  required=False, allow_blank=True)
    whatsapp  = serializers.CharField(max_length=30,  required=False, allow_blank=True)
    file_ine  = serializers.FileField(required=False, allow_null=True)
    foto      = serializers.ImageField(required=False, allow_null=True)

    # ── Paso 3: Acceso y consentimiento ─────────────────────────────────────
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    privacy  = serializers.BooleanField()
    terms    = serializers.BooleanField()

    # ── Validaciones de campo ────────────────────────────────────────────────
    def validate_email(self, email):
        email = email.lower()
        if CuentaProveedor.objects.filter(email=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese correo.")
        return email

    def validate_rfc_empresa(self, rfc):
        if rfc and not rfc_valido(rfc):
            raise serializers.ValidationError("RFC inválido.")
        return (rfc or "").upper().strip() or None

    def validate_curp(self, curp):
        if curp:
            curp = curp.upper().strip()
            if not _CURP_RE.match(curp):
                raise serializers.ValidationError("CURP inválida (18 caracteres, formato oficial).")
        return curp

    def validate_nss(self, nss):
        if nss:
            nss = nss.strip()
            if not nss.isdigit() or len(nss) != 11:
                raise serializers.ValidationError("El NSS debe ser exactamente 11 dígitos.")
        return nss

    def validate_repse(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=10)
        return f

    def validate_sua(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=10)
        return f

    def validate_file_ine(self, f):
        if f:
            validar_archivo(f, extensiones=_DOCS, max_mb=10)
        return f

    def validate_foto(self, f):
        if f:
            validar_archivo(f, extensiones=_FOTOS, max_mb=5)
        return f

    def validate(self, attrs):
        if not attrs.get("privacy"):
            raise serializers.ValidationError({"privacy": "Debes aceptar el Aviso de Privacidad."})
        if not attrs.get("terms"):
            raise serializers.ValidationError({"terms": "Debes aceptar los Términos y Condiciones."})
        return attrs
