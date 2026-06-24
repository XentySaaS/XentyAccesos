"""Siembra los planes comerciales por defecto (idempotente, por clave estable).

Los roles del tenant son enums (``Usuario.Rol``), no requieren tabla ni siembra. Aquí se siembran
los Planes con su lista de módulos (que gobierna ``RequiereModulo``).
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.tenants.models import Plan

TODOS_LOS_MODULOS = [
    "recintos", "proveedores", "empleados", "documentos", "eventos", "citas",
    "acceso", "gafetes", "sanciones", "dispositivos", "mensajeria", "cumplimiento", "ocr",
]

PLANES = [
    {
        "clave": "basico",
        "nombre": "Básico",
        "precio_mensual": 0,
        "modulos": ["recintos", "proveedores", "empleados", "documentos", "eventos", "acceso", "gafetes"],
        "limites": {"usuarios": 5, "eventos": 20},
    },
    {
        "clave": "pro",
        "nombre": "Pro",
        "precio_mensual": 1499,
        "modulos": TODOS_LOS_MODULOS,
        "limites": {"usuarios": 50, "eventos": 500},
    },
]


class Command(BaseCommand):
    help = "Crea/actualiza los planes comerciales por defecto (idempotente)."

    def handle(self, *args, **opts):
        for datos in PLANES:
            plan, creado = Plan.objects.update_or_create(
                clave=datos["clave"],
                defaults={
                    "nombre": datos["nombre"],
                    "precio_mensual": datos["precio_mensual"],
                    "modulos": datos["modulos"],
                    "limites": datos["limites"],
                    "activo": True,
                },
            )
            verbo = "creado" if creado else "actualizado"
            self.stdout.write(self.style.SUCCESS(f"✔ Plan '{plan.clave}' {verbo}."))
