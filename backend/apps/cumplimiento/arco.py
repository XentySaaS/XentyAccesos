"""Motor de derechos ARCO / LFPDPPP (acceso y cancelación) sobre los titulares del tenant.

Titulares cubiertos: Empleado, CuentaProveedor y AsistenteCita (los de PII más sensible: INE, CURP,
NSS, OCR). Todo corre dentro del schema del tenant (aislamiento).

- **Acceso** (`exportar_titular`): reúne y **descifra** la PII del titular + metadatos relacionados,
  para entregársela en formato abierto (portabilidad).
- **Cancelación** (`cancelar_titular`): **anonimización in-place** — sobrescribe la PII, borra los
  archivos privados del disco por tenant y marca la baja lógica, **preservando la fila y la bitácora**
  (FKs `PROTECT`/`SET_NULL` + retención legal). Idempotente.
"""

from __future__ import annotations

from django.utils import timezone

from .models import TitularTipo

PLACEHOLDER = "[Titular cancelado]"


def mascara_nombre(nombre: str | None) -> str:
    """Descripción no-identificable para la bitácora de solicitudes (no guardar PII en claro)."""
    nombre = (nombre or "").strip()
    if not nombre:
        return "—"
    primero = nombre.split()[0]
    return f"{primero[:1]}{'*' * max(2, len(primero) - 1)}"


# ── Resolución de titulares ──────────────────────────────────────────────────
def _modelo(tipo: str):
    from apps.citas.models import AsistenteCita
    from apps.empleados.models import Empleado
    from apps.proveedores.models import CuentaProveedor

    return {
        TitularTipo.EMPLEADO: Empleado,
        TitularTipo.CUENTA_PROVEEDOR: CuentaProveedor,
        TitularTipo.ASISTENTE: AsistenteCita,
    }.get(tipo)


def obtener_titular(tipo: str, titular_id: int):
    modelo = _modelo(tipo)
    if modelo is None:
        return None
    return modelo.objects.filter(pk=titular_id).first()


def buscar_titulares(q: str, limite: int = 20) -> list[dict]:
    """Busca titulares por nombre/email en los tres tipos (para que el admin ubique al solicitante)."""
    from django.db.models import Q

    from apps.citas.models import AsistenteCita
    from apps.empleados.models import Empleado
    from apps.proveedores.models import CuentaProveedor

    q = (q or "").strip()
    if len(q) < 2:
        return []
    filtro = Q(nombre__icontains=q) | Q(email__icontains=q)
    out: list[dict] = []
    for emp in Empleado.objects.filter(filtro)[:limite]:
        out.append(_ref(TitularTipo.EMPLEADO, emp.id, emp.nombre, emp.email, emp.estado))
    for cta in CuentaProveedor.objects.filter(filtro)[:limite]:
        out.append(
            _ref(
                TitularTipo.CUENTA_PROVEEDOR,
                cta.id,
                cta.nombre,
                cta.email,
                "activo" if cta.activo else "baja",
            )
        )
    for asi in AsistenteCita.objects.filter(filtro)[:limite]:
        out.append(_ref(TitularTipo.ASISTENTE, asi.id, asi.nombre, asi.email, None))
    return out


def _ref(tipo: str, tid: int, nombre: str, email: str | None, estado) -> dict:
    return {
        "titular_tipo": tipo,
        "titular_id": tid,
        "nombre": nombre,
        "email": email,
        "estado": estado,
    }


# ── Acceso / portabilidad (export) ───────────────────────────────────────────
def exportar_titular(tipo: str, titular_id: int) -> dict | None:
    """PII descifrada del titular + metadatos relacionados. `None` si no existe."""
    obj = obtener_titular(tipo, titular_id)
    if obj is None:
        return None
    base = {
        "titular_tipo": tipo,
        "titular_id": titular_id,
        "generado": timezone.now().isoformat(),
    }
    if tipo == TitularTipo.EMPLEADO:
        base["datos_personales"] = _export_empleado(obj)
    elif tipo == TitularTipo.CUENTA_PROVEEDOR:
        base["datos_personales"] = _export_cuenta(obj)
    else:
        base["datos_personales"] = _export_asistente(obj)
    return base


def _export_empleado(emp) -> dict:
    from apps.documentos.models import DocumentoEmpleado

    docs = [
        {
            "tipo": getattr(d.tipo_documento, "nombre", None),
            "estado": d.estado,
            "creado": _iso(d.creado),
        }
        for d in DocumentoEmpleado.objects.filter(empleado=emp).select_related("tipo_documento")
    ]
    return {
        "tipo": "empleado",
        "nombre": emp.nombre,
        "email": emp.email,
        "telefono": emp.telefono,
        "estado": emp.estado,
        "tiene_foto": bool(emp.foto),
        "proveedor": getattr(emp.proveedor, "nombre", None),
        "documentos": docs,
        "sanciones": _contar("apps.sanciones.models", "Sancion", empleado=emp),
        "registros_acceso": _contar("apps.acceso.models", "RegistroAcceso", empleado=emp),
        "creado": _iso(emp.creado),
    }


def _export_cuenta(cta) -> dict:
    return {
        "tipo": "cuenta_proveedor",
        "nombre": cta.nombre,
        "apellidos": cta.apellidos,
        "email": cta.email,
        "telefono": cta.telefono,
        "puesto": cta.puesto,
        "curp": cta.curp,  # descifrado por el field al leer
        "nss": cta.nss,
        "activo": cta.activo,
        "tiene_ine": bool(cta.file_ine),
        "tiene_foto": bool(cta.foto),
        "empresa": getattr(cta.proveedor, "nombre", None),
        "creado": _iso(cta.creado),
    }


def _export_asistente(asi) -> dict:
    return {
        "tipo": "asistente",
        "nombre": asi.nombre,
        "email": asi.email,
        "telefono": asi.telefono,
        "ine_data": asi.ine_data,  # JSON descifrado (OCR de INE)
        "numero_identificacion": asi.numero_identificacion,  # descifrado
        "tipo_identificacion": asi.tipo_identificacion,
        "ine_capturado": asi.ine_capturado,
        "tiene_imagen_ine": bool(asi.path_ine),
        "cita_id": asi.cita_id,
        "creado": _iso(asi.creado),
    }


# ── Cancelación (anonimización) ──────────────────────────────────────────────
def cancelar_titular(tipo: str, titular_id: int) -> dict | None:
    """Anonimiza al titular y borra sus archivos privados. Idempotente. `None` si no existe."""
    obj = obtener_titular(tipo, titular_id)
    if obj is None:
        return None
    if tipo == TitularTipo.EMPLEADO:
        _cancelar_empleado(obj)
    elif tipo == TitularTipo.CUENTA_PROVEEDOR:
        _cancelar_cuenta(obj)
    else:
        _cancelar_asistente(obj)
    return {"titular_tipo": tipo, "titular_id": titular_id, "estado": "anonimizado"}


def _cancelar_empleado(emp) -> None:
    from apps.documentos.models import DocumentoEmpleado
    from apps.empleados.models import Empleado

    _borrar_archivo(emp.foto)
    for doc in DocumentoEmpleado.objects.filter(empleado=emp):
        _borrar_archivo(doc.archivo)
        doc.save(update_fields=["archivo"])
    emp.nombre = PLACEHOLDER
    emp.email = None
    emp.telefono = None
    emp.estado = Empleado.Estado.BAJA
    emp.save(update_fields=["nombre", "email", "telefono", "estado", "foto"])


def _cancelar_cuenta(cta) -> None:
    _borrar_archivo(cta.file_ine)
    _borrar_archivo(cta.foto)
    cta.nombre = PLACEHOLDER
    cta.apellidos = None
    # Email es UNIQUE y login: se sustituye por un valor no-identificable pero único.
    cta.email = f"cancelado-{cta.pk}@anonimizado.local"
    cta.telefono = None
    cta.puesto = None
    cta.curp = None
    cta.nss = None
    cta.mfa_habilitado = False
    cta.mfa_totp_secret = None
    cta.activo = False
    cta.set_unusable_password()
    cta.save()


def _cancelar_asistente(asi) -> None:
    _borrar_archivo(asi.path_ine)
    asi.nombre = PLACEHOLDER
    asi.email = None
    asi.telefono = None
    asi.ine_data = None
    asi.numero_identificacion = None
    asi.tipo_identificacion = None
    asi.ine_capturado = False
    asi.save(
        update_fields=[
            "nombre",
            "email",
            "telefono",
            "ine_data",
            "numero_identificacion",
            "tipo_identificacion",
            "ine_capturado",
            "path_ine",
        ]
    )


# ── Utilidades ───────────────────────────────────────────────────────────────
def _borrar_archivo(campo) -> None:
    """Borra el archivo del disco privado del tenant y limpia el campo. Idempotente."""
    if campo:
        campo.delete(save=False)


def _contar(modulo: str, clase: str, **filtros) -> int:
    import importlib

    try:
        modelo = getattr(importlib.import_module(modulo), clase)
        return modelo.objects.filter(**filtros).count()
    except Exception:  # noqa: BLE001 — el export nunca debe romperse por un módulo relacionado
        return 0


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None
