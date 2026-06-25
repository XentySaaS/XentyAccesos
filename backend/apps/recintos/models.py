"""Topología física del recinto (DATA PLANE, schema por tenant).

Contextualiza eventos, citas y accesos. Correcciones sobre el origen (MODELO_DATOS_SAR §6.4):
nombre único **por recinto** (no global), y ``parent_id`` de Ubicación/Entrada como FK self real.

Referencia: MODELO_DATOS_SAR §6.4 · SAR_FUNCIONALIDADES §2.
"""
from __future__ import annotations

from django.db import models


class Recinto(models.Model):  # precincts
    nombre = models.CharField(max_length=200, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    codigo = models.CharField(max_length=60, unique=True, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre or f"Recinto {self.pk}"


class Zona(models.Model):  # zones
    recinto = models.ForeignKey(Recinto, on_delete=models.CASCADE, related_name="zonas")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("recinto", "nombre")]  # FIX: el origen lo tenía único global

    def __str__(self) -> str:
        return self.nombre


class Acceso(models.Model):  # accesses
    recinto = models.ForeignKey(Recinto, on_delete=models.CASCADE, related_name="accesos")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("recinto", "nombre")]

    def __str__(self) -> str:
        return self.nombre


class Ubicacion(models.Model):  # locations
    zona = models.ForeignKey(Zona, on_delete=models.CASCADE, related_name="ubicaciones")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    padre = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="hijas"
    )  # FIX: parent_id ahora FK self real
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre


class Entrada(models.Model):  # entries
    acceso = models.ForeignKey(Acceso, on_delete=models.CASCADE, related_name="entradas")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    padre = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="hijas"
    )  # FIX: parent_id ahora FK self real
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre


class AreaAutorizada(models.Model):  # authorized_areas
    recinto = models.ForeignKey(Recinto, on_delete=models.CASCADE, related_name="areas")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("recinto", "nombre")]

    def __str__(self) -> str:
        return self.nombre


class Protocolo(models.Model):  # protocols
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    archivo = models.FileField(upload_to="protocolos/", null=True, blank=True)  # PDF ≤10MB
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.nombre
