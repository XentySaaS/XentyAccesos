"""Endpoints de autenticación del contexto *proveedores* (autoservicio)."""

from common.auth_api import BaseLoginView
from common.password_reset import ConfirmarResetBase, SolicitarResetBase

from .models import CuentaProveedor


class ProveedorLoginView(BaseLoginView):
    model = CuentaProveedor
    ctx = "proveedores"


class ProveedorSolicitarResetView(SolicitarResetBase):
    model = CuentaProveedor
    ctx = "proveedores"


class ProveedorConfirmarResetView(ConfirmarResetBase):
    model = CuentaProveedor
    ctx = "proveedores"
