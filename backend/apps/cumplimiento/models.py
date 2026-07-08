"""Cumplimiento SAT 69-B (DATA PLANE): espejo de EFOS y resultados de validación.

Referencia: MODELO_DATOS_SAR §6.11 · SAR_FUNCIONALIDADES §13.
"""

from __future__ import annotations

from django.db import models

# El padrón EFOS (SatEfo) es GLOBAL: vive en el app compartido ``apps.efos`` (schema público),
# no aquí. Este app (por tenant) solo guarda las consultas y resultados de validación.


class ConsultaLista69b(models.Model):  # lista_69bs
    tipo = models.IntegerField(default=0)  # 0 = individual, 1 = corrida programada
    creado = models.DateTimeField(auto_now_add=True)


class ResultadoLista69b(models.Model):  # result__lista69bs -> resultados_lista69b
    class Estado(models.IntegerChoices):
        LIMPIO = 0, "Limpio"
        ENCONTRADO = 1, "Encontrado"

    consulta = models.ForeignKey(
        ConsultaLista69b, on_delete=models.CASCADE, related_name="resultados"
    )
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.CASCADE)
    rfc = models.CharField(max_length=13, null=True, blank=True)
    query_data = models.JSONField(null=True, blank=True)
    estado = models.IntegerField(choices=Estado.choices, default=Estado.LIMPIO)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)


# ── ARCO / LFPDPPP (protección de datos personales) ──────────────────────────
class TitularTipo(models.TextChoices):
    """Tipos de titular con PII sujetos a derechos ARCO en el data plane del tenant."""

    EMPLEADO = "empleado", "Empleado"
    CUENTA_PROVEEDOR = "cuenta_proveedor", "Cuenta de proveedor"
    ASISTENTE = "asistente", "Asistente de cita"


class SolicitudArco(models.Model):
    """Solicitud de derechos ARCO y su seguimiento (LFPDPPP art. 32; plazo de respuesta legal).

    Registro auditable: qué derecho ejerció qué titular, estado y **fecha límite de respuesta**
    (20 días naturales por defecto). No guarda PII del titular en claro: solo una descripción
    enmascarada para poder rastrear la solicitud incluso después de anonimizar al titular.
    """

    class Tipo(models.TextChoices):
        ACCESO = "acceso", "Acceso"
        RECTIFICACION = "rectificacion", "Rectificación"
        CANCELACION = "cancelacion", "Cancelación"
        OPOSICION = "oposicion", "Oposición"

    class Estado(models.TextChoices):
        RECIBIDA = "recibida", "Recibida"
        EN_PROCESO = "en_proceso", "En proceso"
        COMPLETADA = "completada", "Completada"
        RECHAZADA = "rechazada", "Rechazada"

    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    titular_tipo = models.CharField(max_length=20, choices=TitularTipo.choices)
    titular_id = models.BigIntegerField()
    titular_desc = models.CharField(max_length=120)  # nombre enmascarado (sin PII en claro)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.RECIBIDA)
    motivo = models.TextField(null=True, blank=True)  # razón de la solicitud o del rechazo
    solicitado_por = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True
    )
    plazo_limite = models.DateField()  # fecha máxima de respuesta legal
    resuelto = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]
        indexes = [models.Index(fields=["titular_tipo", "titular_id"])]


class DocumentoLegal(models.Model):
    """Documento legal del tenant (aviso de privacidad, términos y condiciones), versionado por tipo.

    Cada edición crea una **versión nueva** por tipo (histórico inmutable): hay que poder probar qué
    texto estaba vigente en un momento dado (LFPDPPP art. 15-16). El vigente de un tipo es su versión
    más alta.
    """

    class Tipo(models.TextChoices):
        AVISO_PRIVACIDAD = "aviso_privacidad", "Aviso de Privacidad"
        TERMINOS = "terminos_condiciones", "Términos y Condiciones"

    tipo = models.CharField(max_length=24, choices=Tipo.choices, db_index=True)
    texto = models.TextField()
    version = models.PositiveIntegerField(default=1)
    vigente_desde = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        "accounts.Usuario", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-version"]
        indexes = [models.Index(fields=["tipo", "-version"])]
