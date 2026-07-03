"""Configuración base de pytest para el backend.

Las pruebas que tocan modelos de tenant deben crear/usar un tenant y entrar en su contexto
(``tenant_context``). La suite de aislamiento (desde F1) verifica que un tenant no lee datos de
otro ni del schema ``public``.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
