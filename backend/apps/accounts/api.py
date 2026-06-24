"""Endpoints de autenticación del contexto *acceso* (operación del recinto)."""
from common.auth_api import BaseLoginView

from .models import Usuario


class AccesoLoginView(BaseLoginView):
    model = Usuario
    ctx = "acceso"
