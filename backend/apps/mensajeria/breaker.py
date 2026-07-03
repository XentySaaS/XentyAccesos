"""Circuit breaker por proveedor (ARQUITECTURA_CONNECTOR §9).

Estado en cache Redis, que ya va **prefijada por schema** (``common.cache.tenant_key_func``) → el
breaker es por-tenant sin esfuerzo extra. Modelo: cerrado → (umbral de fallos) → abierto →
(cooldown expira) → semiabierto (siguiente intento sondea) → cerrado si OK / abierto si falla.
"""

from __future__ import annotations

from django.core.cache import cache


class CircuitBreaker:
    def __init__(self, nombre: str, *, umbral: int = 5, cooldown: int = 60, ventana: int = 300):
        self.nombre = nombre
        self.umbral = umbral
        self.cooldown = cooldown
        self.ventana = ventana
        self._k_fallos = f"cb:{nombre}:fallos"
        self._k_open = f"cb:{nombre}:open"

    def permitido(self) -> bool:
        """False si el breaker está abierto (aún en cooldown)."""
        return not cache.get(self._k_open, False)

    def registrar_exito(self) -> None:
        cache.delete(self._k_fallos)
        cache.delete(self._k_open)

    def registrar_fallo(self) -> None:
        try:
            n = cache.incr(self._k_fallos)
        except ValueError:  # clave inexistente
            cache.set(self._k_fallos, 1, self.ventana)
            n = 1
        if n >= self.umbral:
            cache.set(self._k_open, True, self.cooldown)
