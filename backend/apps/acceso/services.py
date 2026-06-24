"""Lógica de acceso físico: validación de escaneo y registro (SAR_FUNCIONALIDADES §9).

Al leer un QR: descifra/verifica firma → pertenencia → vigencia → ``statusdocs`` → sin sanción
activa → registra entrada o denegado. También el auto-registro de walk-in.
"""
from __future__ import annotations

from django.utils import timezone

from apps.gafetes.services import TIPO_CITA, TIPO_EVENTO, TIPO_PARKING, QRInvalido, verificar_qr
from apps.sanciones.models import Sancion

from .models import RegistroAcceso, RegistroAccesoParking


def tiene_sancion_activa(empleado) -> bool:
    """Baja bloquea siempre; Suspensión bloquea dentro de su rango de fechas."""
    hoy = timezone.now().date()
    qs = Sancion.objects.filter(empleado=empleado)
    if qs.filter(penalidad=Sancion.Penalidad.BAJA).exists():
        return True
    return qs.filter(
        penalidad=Sancion.Penalidad.SUSPENSION, fecha_inicio__lte=hoy, fecha_fin__gte=hoy
    ).exists()


def _entrada(**kw) -> RegistroAcceso:
    kw.setdefault("hora_entrada", timezone.now())
    return RegistroAcceso.objects.create(tipo_acceso=RegistroAcceso.TipoAcceso.ENTRADA, **kw)


def _denegar(motivo: str, **kw) -> tuple[RegistroAcceso, bool, str]:
    reg = RegistroAcceso.objects.create(
        tipo_acceso=RegistroAcceso.TipoAcceso.DENEGADO,
        hora_entrada=timezone.now(), observaciones=motivo, **kw,
    )
    return reg, False, motivo


def procesar_escaneo(qr: str, tenant: str, *, placa: str | None = None):
    """Devuelve ``(registro, permitido, motivo)`` tras validar el QR y las reglas de acceso."""
    from apps.eventos.models import CajonParking, EmpleadoEventoProveedor

    try:
        data = verificar_qr(qr, tenant=tenant)
    except QRInvalido as e:
        return _denegar(str(e))

    tipo = data.get("tipo")
    if tipo == TIPO_EVENTO:
        return _escaneo_evento(data["id"], EmpleadoEventoProveedor)
    if tipo == TIPO_CITA:
        return _escaneo_cita(data["id"])
    if tipo == TIPO_PARKING:
        return _escaneo_parking(data["id"], CajonParking, placa)
    return _denegar("Tipo de QR desconocido.")


def _escaneo_evento(eep_id, EmpleadoEventoProveedor):
    eep = (
        EmpleadoEventoProveedor.objects
        .select_related("evento_proveedor__evento", "empleado").filter(id=eep_id).first()
    )
    if eep is None:
        return _denegar("Asignación no encontrada.")
    evento = eep.evento_proveedor.evento
    hoy = timezone.now().date()
    if not (evento.vigencia_inicio <= hoy <= evento.vigencia_fin):
        return _denegar("Fuera de la vigencia del evento.", empleado=eep.empleado, evento=evento)
    if eep.statusdocs != eep.StatusDocs.CUMPLE:
        return _denegar("Documentos no verificados.", empleado=eep.empleado, evento=evento)
    if tiene_sancion_activa(eep.empleado):
        return _denegar("Empleado con sanción activa.", empleado=eep.empleado, evento=evento)
    reg = _entrada(empleado=eep.empleado, evento=evento, metodo=RegistroAcceso.Metodo.QR)
    return reg, True, "Acceso concedido."


def _escaneo_cita(asistente_id):
    from apps.citas.models import AsistenteCita, Cita

    asis = AsistenteCita.objects.select_related("cita").filter(id=asistente_id).first()
    if asis is None:
        return _denegar("Asistente no encontrado.")
    if asis.cita.estado == Cita.Estado.CANCELADA:
        return _denegar("La cita está cancelada.", cita=asis.cita)
    reg = _entrada(asistente=asis, cita=asis.cita, metodo=RegistroAcceso.Metodo.QR)
    return reg, True, "Acceso concedido."


def _escaneo_parking(cajon_id, CajonParking, placa):
    cajon = CajonParking.objects.filter(id=cajon_id).first()
    if cajon is None:
        return _denegar("Cajón de parking no encontrado.")
    reg = RegistroAccesoParking.objects.create(
        cajon=cajon, tipo_acceso=RegistroAccesoParking.TipoAcceso.ENTRADA,
        hora_entrada=timezone.now(), placa_vehiculo=placa,
    )
    return reg, True, "Acceso de parking concedido."


def registrar_walkin(cita) -> RegistroAcceso:
    """Walk-in: crea automáticamente el registro de entrada de la cita (SAR_FUNC §7.1)."""
    return _entrada(cita=cita, metodo=RegistroAcceso.Metodo.MANUAL)
