"""Importa el padrón SAT 69-B (EFOS) al espejo del tenant y revalida proveedores.

Fuente (gratuita): el CSV público del SAT. Se puede tomar de un archivo local o de una URL.

Ejemplos:
  python manage.py importar_efos --schema rayados --archivo lista69b.csv
  python manage.py importar_efos --schema rayados --url http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv
  python manage.py importar_efos --all-tenants          # usa SAT_EFOS_CSV_URL
  python manage.py importar_efos --schema rayados --no-revalidar
"""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, schema_context

from apps.cumplimiento.services import importar_efos, revalidar_todos

_SAT_URL_DEFAULT = "http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv"


class Command(BaseCommand):
    help = "Importa el CSV de EFOS (SAT 69-B) al espejo del tenant y revalida proveedores."

    def add_arguments(self, parser):
        parser.add_argument("--schema", help="Schema del tenant destino.")
        parser.add_argument("--all-tenants", action="store_true", help="Aplica a todos los tenants.")
        parser.add_argument("--archivo", help="Ruta a un CSV local (bytes, cualquier codificación).")
        parser.add_argument("--url", help="URL del CSV (default: SAT_EFOS_CSV_URL o la del SAT).")
        parser.add_argument("--no-revalidar", action="store_true",
                            help="No revalida proveedores tras importar.")

    def handle(self, *args, **opts):
        contenido = self._obtener_contenido(opts)  # bytes

        if opts["all_tenants"]:
            schemas = self._tenants()
        elif opts["schema"]:
            schemas = [opts["schema"]]
        else:
            raise CommandError("Indica --schema <slug> o --all-tenants.")

        for schema in schemas:
            with schema_context(schema):
                res = importar_efos(contenido)
                msg = f"[{schema}] EFOS: {res}"
                if not opts["no_revalidar"]:
                    rev = revalidar_todos()
                    msg += f" · revalidados={rev['revisados']} encontrados={rev['encontrados']}"
                self.stdout.write(self.style.SUCCESS(msg))

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
        return [
            t.schema_name for t in get_tenant_model().objects.all()
            if t.schema_name != publico
        ]
