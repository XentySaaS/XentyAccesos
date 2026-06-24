"""ETL MySQL→PostgreSQL por tenant (MIGRACION_DATOS_SAR.md).

Orquesta EXTRACT→TRANSFORM→LOAD→VALIDATE. La extracción real corre contra el MySQL de producción
(solo lectura) configurado en ``MYSQL_SAR_DSN``; la capa TRANSFORM vive en ``etl.transformers``.

Uso:
    python manage.py migrar_tenant_sar <subdominio> --dry-run
    python manage.py migrar_tenant_sar <subdominio> [--solo recintos,eventos]
"""
from __future__ import annotations

from decouple import config
from django.core.management.base import BaseCommand, CommandError

# Orden de carga por dependencias de FK (MIGRACION_DATOS_SAR §4).
ORDEN_CARGA = [
    "recintos (Recinto→Zona/Acceso→Ubicacion/Entrada→AreaAutorizada; Protocolo)",
    "identidad (Usuario; Proveedor→CuentaProveedor→Empleado)",
    "documentos (GrupoDocumentos→TipoDocumento)",
    "eventos (Evento→EventoProveedor→CajonParking; pivotes)",
    "citas (Contacto; Cita→AsistenteCita [resolver person_id]; EmpleadoCita)",
    "documentos de empleado (DocumentoEmpleado verified 0/1/2)",
    "operacion (RegistroAcceso, RegistroAccesoParking; Sancion)",
    "comunicacion/cumplimiento (Mensaje→Destinatario; SatEfo, 69-b)",
    "config/auditoria (Opcion; HistorialCambio)",
]


class Command(BaseCommand):
    help = "ETL MySQL→Postgres por tenant (re-cifra PII, reemite QR, valida conteos)."

    def add_arguments(self, parser):
        parser.add_argument("subdominio")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--solo", default="", help="lista de bloques separados por coma")

    def handle(self, *args, **opts):
        from apps.tenants.models import Tenant

        slug = opts["subdominio"].strip().lower()
        tenant = Tenant.objects.filter(schema_name=slug).first()
        if tenant is None:
            raise CommandError(f"No existe el tenant destino '{slug}' (provisiónalo antes).")

        bloques = [b.strip() for b in opts["solo"].split(",") if b.strip()] or ORDEN_CARGA
        self.stdout.write(self.style.MIGRATE_HEADING(f"Plan ETL para '{slug}':"))
        for i, bloque in enumerate(bloques, 1):
            self.stdout.write(f"  {i}. {bloque}")

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run: no se escribió nada. TRANSFORM listo en etl.transformers."))
            return

        dsn = config("MYSQL_SAR_DSN", default="")
        if not dsn:
            raise CommandError(
                "Configura MYSQL_SAR_DSN para la extracción real (MySQL de producción, solo lectura). "
                "Ver MIGRACION_DATOS_SAR.md §2."
            )
        # EXTRACT (MySQL) → TRANSFORM (etl.transformers) → LOAD (ORM en tenant_context) → FILES →
        # REISSUE (QR firmados) → VALIDATE (conteos/integridad/PII/aislamiento).
        raise CommandError(
            "Extracción MySQL no disponible en este entorno; ejecutar contra el origen productivo."
        )
