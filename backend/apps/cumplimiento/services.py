"""Importador del padrón 69-B (EFOS) del SAT y validación de proveedores.

El CSV oficial del SAT (``Listado_Completo_69-B.csv``) NO trae encabezados limpios en la primera
línea: incluye filas de título y los encabezados reales aparecen más abajo, con acentos
("Situación del contribuyente") y suele venir en Latin-1/CP1252. Por eso el parser:
  1. Decodifica tolerante a codificación (utf-8-sig → cp1252 → latin-1).
  2. Detecta dinámicamente la fila de encabezado (la primera que contiene RFC y Situación),
     en vez de asumir un índice fijo.
  3. Mapea columnas sin acentos/insensible a mayúsculas.
El servicio es gratuito: solo descarga/lee el CSV público del SAT.

Estatus bloqueantes configurables (``SAT_EFOS_ESTATUS_BLOQUEANTES``, default Definitivo/Presunto).
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata

from django.conf import settings

from apps.efos.models import SatEfo

from .models import ConsultaLista69b, ResultadoLista69b


def _norm(texto: str | None) -> str:
    """Minúsculas, sin acentos, alfanumérico con guion bajo (para comparar encabezados/estatus)."""
    base = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")


def estatus_bloqueantes() -> set[str]:
    return set(getattr(settings, "SAT_EFOS_ESTATUS_BLOQUEANTES", ["Definitivo", "Presunto"]))


def situacion_bloqueante(situacion: str | None) -> bool:
    """¿La situación del EFO bloquea? Compara sin acentos/mayúsculas y por prefijo.

    Así 'Definitivo', 'Definitivos', 'DEFINITIVO' coinciden con el estatus configurado 'Definitivo'.
    """
    n = _norm(situacion)
    if not n:
        return False
    return any(_norm(b) and _norm(b) in n for b in estatus_bloqueantes())


def _decodificar(contenido: bytes | str) -> str:
    if isinstance(contenido, str):
        return contenido
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return contenido.decode(enc)
        except UnicodeDecodeError:
            continue
    return contenido.decode("utf-8", errors="replace")


def _localizar_encabezado(filas: list[list[str]]) -> tuple[int, dict[str, int]]:
    """Devuelve (índice de la fila de encabezado, {columna_normalizada: índice})."""
    for i, fila in enumerate(filas[:15]):
        norm = [_norm(c) for c in fila]
        if "rfc" in norm and any(c.startswith("situacion") for c in norm):
            return i, {c: j for j, c in enumerate(norm) if c}
    raise ValueError("No se encontró el encabezado (RFC / Situación) en el CSV del SAT.")


def importar_efos(contenido: bytes | str) -> dict:
    """Carga/actualiza el espejo de EFOS desde el CSV oficial (idempotente por RFC).

    Acepta texto o bytes crudos (para manejar la codificación del SAT). Devuelve un resumen.
    """
    texto = _decodificar(contenido)
    filas = list(csv.reader(io.StringIO(texto)))
    if not filas:
        return {"creados": 0, "actualizados": 0, "total": 0}

    idx_header, cols = _localizar_encabezado(filas)
    idx_rfc = cols["rfc"]
    idx_sit = next(j for c, j in cols.items() if c.startswith("situacion"))
    idx_nom = next((j for c, j in cols.items() if c.startswith("nombre")), None)

    from django.utils import timezone

    ahora = timezone.now()
    objetos: list[SatEfo] = []
    vistos: set[str] = set()
    for fila in filas[idx_header + 1:]:
        if len(fila) <= idx_rfc:
            continue
        rfc = (fila[idx_rfc] or "").strip().upper()
        if not rfc or not re.fullmatch(r"[A-ZÑ&0-9]{10,13}", rfc) or rfc in vistos:
            continue
        vistos.add(rfc)
        situacion = ((fila[idx_sit] or "").strip() if len(fila) > idx_sit else "")[:60]
        nombre = (fila[idx_nom] or "").strip() if idx_nom is not None and len(fila) > idx_nom else ""
        objetos.append(SatEfo(rfc=rfc, situacion=situacion, nombre=nombre, creado=ahora, actualizado=ahora))

    # Upsert masivo (INSERT ... ON CONFLICT): ~14k filas en pocos statements en vez de 28k queries.
    # bulk_create no dispara auto_now, por eso fijamos actualizado explícitamente (para el dashboard).
    SatEfo.objects.bulk_create(
        objetos,
        update_conflicts=True,
        unique_fields=["rfc"],
        update_fields=["nombre", "situacion", "actualizado"],
        batch_size=1000,
    )
    return {"total": len(objetos)}


def validar_69b(proveedor, tipo: int = 0) -> ResultadoLista69b:
    """Valida el RFC del proveedor contra EFOS y registra el resultado."""
    rfc = (proveedor.rfc or "").upper().strip()
    consulta = ConsultaLista69b.objects.create(tipo=tipo)
    efo = SatEfo.objects.filter(rfc=rfc).first() if rfc else None
    bloqueado = bool(efo and situacion_bloqueante(efo.situacion))
    estado = (
        ResultadoLista69b.Estado.ENCONTRADO if bloqueado else ResultadoLista69b.Estado.LIMPIO
    )
    return ResultadoLista69b.objects.create(
        consulta=consulta, proveedor=proveedor, rfc=rfc, estado=estado,
        query_data={
            "situacion": efo.situacion if efo else None,
            "nombre_sat": efo.nombre if efo else None,
            "bloqueado": bloqueado,
        },
    )


def revalidar_todos(tipo: int = 1) -> dict:
    """Revalida a todos los proveedores contra el padrón EFOS actual. Devuelve un resumen.

    Registra un resultado por proveedor en una sola corrida. Sirve para re-evaluar tras cada
    actualización del padrón (un proveedor limpio hoy puede aparecer mañana).
    """
    from apps.proveedores.models import Proveedor

    consulta = ConsultaLista69b.objects.create(tipo=tipo)
    encontrados: list[dict] = []
    revisados = 0
    for proveedor in Proveedor.objects.all():
        rfc = (proveedor.rfc or "").upper().strip()
        efo = SatEfo.objects.filter(rfc=rfc).first() if rfc else None
        bloqueado = bool(efo and situacion_bloqueante(efo.situacion))
        estado = ResultadoLista69b.Estado.ENCONTRADO if bloqueado else ResultadoLista69b.Estado.LIMPIO
        ResultadoLista69b.objects.create(
            consulta=consulta, proveedor=proveedor, rfc=rfc, estado=estado,
            query_data={"situacion": efo.situacion if efo else None, "bloqueado": bloqueado},
        )
        revisados += 1
        if bloqueado:
            encontrados.append({
                "proveedor_id": proveedor.id, "proveedor": proveedor.nombre,
                "rfc": rfc, "situacion": efo.situacion,
            })
    return {"revisados": revisados, "encontrados": len(encontrados), "detalle": encontrados}
