"""Endpoints de autenticación del contexto *acceso* (operación del recinto)."""

from common.auth_api import BaseLoginView
from common.password_reset import ConfirmarResetBase, SolicitarResetBase

from .models import Usuario


class AccesoLoginView(BaseLoginView):
    model = Usuario
    ctx = "acceso"


class AccesoSolicitarResetView(SolicitarResetBase):
    model = Usuario
    ctx = "acceso"


class AccesoConfirmarResetView(ConfirmarResetBase):
    model = Usuario
    ctx = "acceso"
