"""``Empleado``: plantilla de la empresa proveedora (DATA PLANE, schema por tenant).

La baja es lógica (``estado=baja``): congela, nunca se borra físicamente (MODELO §1.6). El email
no es único (el origen quitó esa restricción).

Referencia: MODELO_DATOS_SAR §6.3 · SAR_FUNCIONALIDADES §4.
"""
from __future__ import annotations

from django.db import models


class Empleado(models.Model):  # employees
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"  # terminated

    # provider_id del origen apunta a la cuenta (CuentaProveedor), no a la empresa (MODELO §6.3).
    proveedor = models.ForeignKey(
        "proveedores.CuentaProveedor", on_delete=models.CASCADE, related_name="empleados"
    )
    nombre = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)  # NO único (el origen lo removió)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    foto = models.ImageField(upload_to="empleados/fotos/", null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre
