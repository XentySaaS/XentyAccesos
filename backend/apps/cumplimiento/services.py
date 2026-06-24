"""Importador del CSV 69-B y validación de proveedores contra EFOS.

Estatus bloqueantes configurables (``SAT_EFOS_ESTATUS_BLOQUEANTES``, default Definitivo/Presunto).
"""
from __future__ import annotations

import csv
import io

from django.conf import settings

from .models import ConsultaLista69b, ResultadoLista69b, SatEfo


def estatus_bloqueantes() -> set[str]:
    return set(getattr(settings, "SAT_EFOS_ESTATUS_BLOQUEANTES", ["Definitivo", "Presunto"]))


def importar_efos(csv_texto: str) -> dict:
    """Carga/actualiza el espejo de EFOS desde el CSV oficial (idempotente por RFC)."""
    lector = csv.DictReader(io.StringIO(csv_texto))
    creados = actualizados = 0
    for fila in lector:
        rfc = (fila.get("rfc") or fila.get("RFC") or "").strip().upper()
        if not rfc:
            continue
        situacion = (fila.get("situacion") or fila.get("Situación del contribuyente") or "").strip()
        nombre = (fila.get("nombre") or fila.get("Nombre del Contribuyente") or "").strip()
        _, creado = SatEfo.objects.update_or_create(
            rfc=rfc, defaults={"situacion": situacion, "nombre": nombre}
        )
        creados += int(creado)
        actualizados += int(not creado)
    return {"creados": creados, "actualizados": actualizados}


def validar_69b(proveedor, tipo: int = 0) -> ResultadoLista69b:
    """Valida el RFC del proveedor contra EFOS y registra el resultado."""
    rfc = (proveedor.rfc or "").upper().strip()
    consulta = ConsultaLista69b.objects.create(tipo=tipo)
    efo = SatEfo.objects.filter(rfc=rfc).first() if rfc else None
    bloqueado = bool(efo and efo.situacion in estatus_bloqueantes())
    estado = (
        ResultadoLista69b.Estado.ENCONTRADO if bloqueado else ResultadoLista69b.Estado.LIMPIO
    )
    return ResultadoLista69b.objects.create(
        consulta=consulta, proveedor=proveedor, rfc=rfc, estado=estado,
        query_data={"situacion": efo.situacion if efo else None, "bloqueado": bloqueado},
    )
