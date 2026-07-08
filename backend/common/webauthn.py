"""WebAuthn / FIDO2 (passkeys y llaves de seguridad) como 2º factor de MFA.

Reutiliza el mismo flujo de sesión que el TOTP (``mfa="pending"`` → ``"ok"``). Es **segundo factor**,
no passwordless: el login por contraseña ya emitió un token pendiente, así que el usuario ya es
conocido y las opciones de autenticación se generan solo para SUS credenciales.

Cada authenticatable guarda sus credenciales en SU schema (SuperAdmin en ``public``, Usuario en el
schema del tenant), mediante subclases concretas de ``CredencialWebAuthnBase``. El reto (challenge)
de cada ceremonia se guarda en cache (Redis) con TTL corto, tipado por propósito + ctx + usuario.
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db import models
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

_TTL_CHALLENGE = 300  # segundos


class CredencialWebAuthnBase(models.Model):
    """Credencial FIDO2 registrada por un actor. La subclase concreta añade el FK al authenticatable.

    ``public_key`` NO es secreto (es la clave pública del autenticador), por eso no se cifra.
    ``sign_count`` es el contador anti-clonación que se actualiza en cada autenticación.
    """

    credential_id = models.CharField(max_length=255, unique=True, db_index=True)  # base64url
    public_key = models.TextField()  # base64url
    sign_count = models.PositiveBigIntegerField(default=0)
    transports = models.CharField(max_length=120, null=True, blank=True)  # "usb,nfc,internal"
    nombre = models.CharField(max_length=80, default="Llave de seguridad")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-creado"]


# ── Config ───────────────────────────────────────────────────────────────────
def _rp_id() -> str:
    return getattr(settings, "WEBAUTHN_RP_ID", "localhost")


def _rp_name() -> str:
    return getattr(settings, "WEBAUTHN_RP_NAME", "Xenty Acceso")


def _origins() -> list[str]:
    orig = getattr(settings, "WEBAUTHN_ORIGINS", None)
    if not orig:
        return ["http://localhost:8080"]
    return list(orig) if isinstance(orig, list | tuple) else [orig]


def cred_model(ctx: str):
    """Modelo de credencial WebAuthn del contexto (super-admin en public, Usuario en tenant)."""
    from apps.accounts.models import CredencialWebAuthn
    from apps.tenants.models import CredencialWebAuthnAdmin

    return {"superadmin": CredencialWebAuthnAdmin, "acceso": CredencialWebAuthn}.get(ctx)


def _fk_name(ctx: str) -> str:
    return {"superadmin": "superadmin", "acceso": "usuario"}[ctx]


def _clave(purpose: str, ctx: str, schema: str, pk) -> str:
    return f"webauthn:{purpose}:{ctx}:{schema}:{pk}"


def _creds(user):
    """Credenciales del actor (relación inversa uniforme en ambas subclases)."""
    return list(user.credenciales_webauthn.all())


# ── Registro (enrolamiento de una credencial) ────────────────────────────────
def opciones_registro(user, ctx: str, schema: str) -> dict:
    excluir = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in _creds(user)
    ]
    opciones = generate_registration_options(
        rp_id=_rp_id(),
        rp_name=_rp_name(),
        user_name=getattr(user, "email", str(user.pk)),
        user_id=str(user.pk).encode(),
        exclude_credentials=excluir,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED
        ),
    )
    cache.set(
        _clave("reg", ctx, schema, user.pk), bytes_to_base64url(opciones.challenge), _TTL_CHALLENGE
    )
    import json

    return json.loads(options_to_json(opciones))


def registrar(
    user, ctx: str, schema: str, credential: dict, nombre: str | None
) -> tuple[bool, str]:
    reto_b64 = cache.get(_clave("reg", ctx, schema, user.pk))
    if not reto_b64:
        return False, "El reto de registro expiró. Inténtalo de nuevo."
    try:
        verificado = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(reto_b64),
            expected_rp_id=_rp_id(),
            expected_origin=_origins(),
        )
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de attestation → registro inválido
        return False, f"No se pudo validar la credencial: {exc}"

    cache.delete(_clave("reg", ctx, schema, user.pk))
    modelo = cred_model(ctx)
    transports = ",".join(credential.get("response", {}).get("transports", []) or []) or None
    modelo.objects.create(
        **{_fk_name(ctx): user},
        credential_id=bytes_to_base64url(verificado.credential_id),
        public_key=bytes_to_base64url(verificado.credential_public_key),
        sign_count=verificado.sign_count,
        transports=transports,
        nombre=(nombre or "Llave de seguridad")[:80],
    )
    if not user.mfa_habilitado:
        user.mfa_habilitado = True
        user.save(update_fields=["mfa_habilitado"])
    return True, ""


# ── Login (2º factor) ─────────────────────────────────────────────────────────
def opciones_login(user, ctx: str, schema: str) -> dict:
    permitidas = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in _creds(user)
    ]
    opciones = generate_authentication_options(rp_id=_rp_id(), allow_credentials=permitidas)
    cache.set(
        _clave("login", ctx, schema, user.pk),
        bytes_to_base64url(opciones.challenge),
        _TTL_CHALLENGE,
    )
    import json

    return json.loads(options_to_json(opciones))


def verificar_login(user, ctx: str, schema: str, credential: dict) -> tuple[bool, str]:
    reto_b64 = cache.get(_clave("login", ctx, schema, user.pk))
    if not reto_b64:
        return False, "El reto de autenticación expiró. Inténtalo de nuevo."
    cred_id = credential.get("id") or credential.get("rawId")
    cred = next((c for c in _creds(user) if c.credential_id == cred_id), None)
    if cred is None:
        return False, "Credencial no reconocida."
    try:
        verificado = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(reto_b64),
            expected_rp_id=_rp_id(),
            expected_origin=_origins(),
            credential_public_key=base64url_to_bytes(cred.public_key),
            credential_current_sign_count=cred.sign_count,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"No se pudo validar la llave: {exc}"

    cache.delete(_clave("login", ctx, schema, user.pk))
    # Anti-clonación: el contador debe avanzar (o quedarse en 0 para autenticadores que no lo usan).
    cred.sign_count = verificado.new_sign_count
    cred.save(update_fields=["sign_count"])
    return True, ""
