"""Actualiza el padrón SAT 69-B (EFOS) GLOBAL y revalida proveedores por tenant.

El padrón es compartido (schema público): se importa UNA vez. La validación es por tenant.
Fuente gratuita: el CSV público del SAT (archivo local o URL).

Ejemplos:
  python manage.py importar_efos                       # descarga del SAT + revalida todos los tenants
  python manage.py importar_efos --archivo lista69b.csv
  python manage.py importar_efos --url http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv
  python manage.py importar_efos --schema rayados      # revalida solo ese tenant
  python manage.py importar_efos --no-revalidar        # solo actualiza el padrón
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, schema_context

from apps.cumplimiento.services import importar_efos, revalidar_todos

_SAT_URL_DEFAULT = "http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv"


class Command(BaseCommand):
    help = "Actualiza el padrón EFOS (SAT 69-B) global y revalida proveedores por tenant."

    def add_arguments(self, parser):
        parser.add_argument("--schema", help="Revalidar solo este tenant (por defecto: todos).")
        parser.add_argument(
            "--archivo", help="Ruta a un CSV local (bytes, cualquier codificación)."
        )
        parser.add_argument("--url", help="URL del CSV (default: SAT_EFOS_CSV_URL o la del SAT).")
        parser.add_argument(
            "--no-revalidar",
            action="store_true",
            help="Solo actualiza el padrón; no revalida proveedores.",
        )

    def handle(self, *args, **opts):
        contenido = self._obtener_contenido(opts)  # bytes

        # Padrón GLOBAL: se importa una sola vez (schema público).
        res = importar_efos(contenido)
        self.stdout.write(self.style.SUCCESS(f"Padrón EFOS actualizado (global): {res}"))

        if opts["no_revalidar"]:
            return

        schemas = [opts["schema"]] if opts["schema"] else self._tenants()
        for schema in schemas:
            with schema_context(schema):
                rev = revalidar_todos()
            self.stdout.write(
                f"[{schema}] revalidados={rev['revisados']} encontrados={rev['encontrados']}"
            )

    def _obtener_contenido(self, opts) -> bytes:
        if opts["archivo"]:
            try:
                with open(opts["archivo"], "rb") as f:
                    return f.read()
            except OSError as exc:
                raise CommandError(str(exc))
        url = opts["url"] or settings.SAT_EFOS_CSV_URL or _SAT_URL_DEFAULT
        try:
            import requests

            r = requests.get(url, timeout=120)
            r.raise_for_status()
            return r.content
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"No se pudo descargar el CSV del SAT ({url}): {exc}")

    def _tenants(self) -> list[str]:
        from django_tenants.utils import get_tenant_model

        publico = get_public_schema_name()
        return [t.schema_name for t in get_tenant_model().objects.all() if t.schema_name != publico]
