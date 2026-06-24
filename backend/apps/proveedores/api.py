"""Endpoints de autenticación del contexto *proveedores* (autoservicio)."""
from common.auth_api import BaseLoginView

from .models import CuentaProveedor


class ProveedorLoginView(BaseLoginView):
    model = CuentaProveedor
    ctx = "proveedores"
