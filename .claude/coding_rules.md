# Reglas de Desarrollo — Xenty Acceso

## Python

- PEP8 + `ruff check . && ruff format .`
- Type hints en servicios y modelos
- `snake_case` funciones/variables, `PascalCase` clases/modelos
- Modelos y `verbose_name` en español
- Docstrings Google style (solo cuando aportan valor)
- Sin comentarios obvios — solo el "por qué" no evidente

## TypeScript / React

- ESLint + Prettier
- Sin `any` — tipar todo
- `camelCase` variables, `PascalCase` componentes/tipos
- Componentes funcionales con hooks
- Estado con Zustand (no Context para estado global)

## Imports (Python)

```python
# 1. stdlib
from __future__ import annotations
import json

# 2. third-party
from rest_framework import viewsets
from django.db import models

# 3. project
from common.permissions import PERMISOS_BASE
from apps.config.services import AuditViewSetMixin

# 4. local
from .models import MiModelo
from .serializers import MiSerializer
```

## Permisos (composición estándar)

```python
# Contexto acceso (operación del recinto)
_PERMS = [
    *PERMISOS_BASE(),
    ContextoAcceso,
    RequiereModulo("modulo"),
    RequiereRol("administrador", "editor", ...),
    RequierePermisoPersonalizado("modulo"),
]

# Contexto proveedores (autoservicio)
_PERMS = [
    *PERMISOS_BASE(),
    ContextoProveedores,
    RequiereModulo("modulo"),
]
```

## ViewSet pattern

```python
class MiViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = MiModelo.objects.none()  # REQUERIDO si usas get_queryset()
    serializer_class = MiSerializer
    permission_classes = _PERMS
    parser_classes = [JSONParser, MultiPartParser, FormParser]  # si recibe archivos
    filterset_fields = ["campo1", "campo2"]

    def get_queryset(self):
        qs = MiModelo.objects.select_related(...).order_by("-id")
        if self.request.user.rol != Usuario.Rol.ADMINISTRADOR:
            qs = qs.filter(creado_por=self.request.user)
        return qs
```

## Serializer pattern

```python
class MiSerializer(serializers.ModelSerializer):
    campo_display = serializers.CharField(source="get_campo_display", read_only=True)

    class Meta:
        model = MiModelo
        fields = ["id", "campo", "campo_display", ...]
        read_only_fields = ["campo_auto"]
```

## Enums

```python
class Estado(models.TextChoices):
    ACTIVO = "activo", "Activo"
    INACTIVO = "inactivo", "Inactivo"
```

Nunca IDs hardcodeados ni enums crudos.

## Error handling

- Validar solo en fronteras del sistema (user input, APIs externas)
- No agregar try/catch defensivo para código interno
- DRF maneja ValidationError automáticamente
- `raise PermissionDenied("mensaje")` para bloqueos de negocio

## Commits

Formato convencional: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`

```
feat(modulo): descripción corta del cambio

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Archivos

- Nombres de archivo: `snake_case.py`, `PascalCase.tsx`
- No crear archivos de documentación (.md) salvo los del sistema de docs/
- Preferir editar archivos existentes a crear nuevos
