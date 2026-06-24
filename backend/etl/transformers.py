"""TRANSFORM del ETL: mapas de enum, normalización y polimorfismo (MIGRACION_DATOS_SAR §4.2).

Funciones puras (sin DB) para poder probarlas con un dataset sintético. El re-cifrado de PII es
automático: el ORM cifra al escribir en los campos ``Encrypted*`` (MIGRACION §5).
"""
from __future__ import annotations

# ── Mapas de enum (origen inglés → destino español) ──────────────────────────
ROL_USUARIO = {
    "Administrator": "administrador", "Editor": "editor", "Security Guard": "guardia",
    "Manager": "gerente", "Receptionist": "recepcion", "User": "usuario", "Verifier": "verificador",
}
ROL_PROVEEDOR = {"Admin": "admin", "User": "usuario"}
ESTADO_GENERICO = {
    "active": "activo", "inactive": "inactivo", "pending": "pendiente",
    "confirmed": "confirmado", "terminated": "baja",
}
EVENTO_ESTADO = {
    "scheduled": "programado", "ongoing": "en_curso", "completed": "completado",
    "cancelled": "cancelado",
}
CITA_ESTADO = {"pending": "pendiente", "confirmed": "confirmada", "cancelled": "cancelada"}
APPOINTMENT_TYPE = {"scheduled": "programada", "walk-in": "walk_in", "emergency": "emergencia"}
ACCESS_TYPE = {"entry": "entrada", "denied": "denegado"}
ACCESS_METHOD = {"QR": "qr", "placa": "placa", "manual": "manual", "tarjeta": "tarjeta"}
SEVERIDAD = {"Bajo": "bajo", "Medio": "medio", "Alto": "alto"}
PENALTY = {"Advertencia": "advertencia", "Suspensión": "suspension", "Baja": "baja"}
MENSAJE_STATUS = {0: 0, 1: 1, 2: 2, 3: 3}  # pendiente/en_progreso/cancelado/completado
RECIPIENT_STATUS = {"pending": "pendiente", "sent": "enviado", "failed": "fallido"}


def mapear(tabla: dict, valor, *, defecto=None):
    """Mapea ``valor`` según ``tabla``; si no existe, devuelve ``defecto`` (o el valor original)."""
    if valor is None:
        return defecto
    return tabla.get(valor, defecto if defecto is not None else valor)


def normalizar_rfc(rfc: str | None) -> str | None:
    return rfc.strip().upper() if rfc else None


def mapear_verified(v) -> int:
    """``employee_documents.verified`` (drift boolean/int) → IntegerChoices 0/1/2.

    true→VERIFICADO(1), false→PENDIENTE(0), 2→RECHAZADO(2).
    """
    if v in (2, "2"):
        return 2
    if v in (True, 1, "1", "true", "True"):
        return 1
    return 0


def resolver_persona(tipo) -> str:
    """``assistent_appointments.type`` → modelo destino del GenericForeignKey."""
    return "empleado" if tipo in (1, "1") else "contacto"


def baja_logica_usuario(low_login, delete_at) -> tuple[bool, object]:
    """``low_login``/``delete_at`` del origen → (``activo``, ``fecha_baja``)."""
    dado_de_baja = bool(low_login) or bool(delete_at)
    return (not dado_de_baja, delete_at if dado_de_baja else None)
