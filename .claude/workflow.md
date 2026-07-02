# Flujo de Trabajo — Xenty Acceso

## Inicio de sesión nueva

1. Leer `CLAUDE.md` (reglas operativas)
2. Leer `handoffs/HANDOFF_LATEST.md` (estado actual)
3. Verificar backend: `docker compose ps backend`
4. Empezar la tarea solicitada

## Durante el desarrollo

### Después de cambiar archivos Python
```bash
docker compose restart backend
```

### Después de cambiar modelos (agregar/modificar fields)
```bash
docker compose exec backend python manage.py makemigrations {app}
docker compose exec backend python manage.py migrate_schemas --shared
docker compose exec backend python manage.py migrate_schemas --tenant
docker compose restart backend
```

### Después de agregar un ViewSet nuevo
1. Registrar en `apps/{modulo}/urls.py`
2. Incluir en `config/urls.py` (data plane) o `config/urls_public.py` (control plane)
3. Agregar `parser_classes` si recibe archivos
4. Mantener `queryset = Model.objects.none()` si usa `get_queryset()`

## Después de completar una tarea significativa

1. **`docs/STATUS.md`** — si cambió estado de un módulo
2. **`docs/CHANGELOG.md`** — registrar el cambio (append, nunca eliminar)
3. **`docs/DECISIONS.md`** — si hubo decisión técnica (append-only)
4. **`docs/KNOWN_ISSUES.md`** — si se encontró o resolvió un issue
5. **`docs/TODOS.md`** — marcar tarea como done, agregar nuevas
6. **`docs/ARCHITECTURE.md`** — si cambió la arquitectura
7. **`docs/ROADMAP.md`** — si cambió la planificación

## Comandos de finalización de sesión

Cuando el usuario escriba cualquiera de estos:
- "Genera handoff"
- "Finalizar sesión"
- "Preparar siguiente conversación"

Ejecutar automáticamente:

1. Actualizar `docs/STATUS.md`
2. Actualizar `docs/CHANGELOG.md`
3. Actualizar `docs/DECISIONS.md` (si hubo decisiones)
4. Actualizar `docs/ROADMAP.md` (si cambió planificación)
5. Actualizar `docs/TODOS.md` (marcar completados, agregar nuevos)
6. Actualizar `docs/KNOWN_ISSUES.md` (si hubo issues)
7. Mover `handoffs/HANDOFF_LATEST.md` actual a `handoffs/history/HANDOFF_{fecha}.md`
8. Generar nuevo `handoffs/HANDOFF_LATEST.md`
9. Informar al usuario: "Para continuar en una nueva conversación, comparte: `CLAUDE.md` + `handoffs/HANDOFF_LATEST.md`"

## Compresión de contexto

- Si una respuesta ya está documentada, referenciar el archivo en lugar de repetirla
- No re-explicar decisiones de `docs/DECISIONS.md`
- No repetir info de `CLAUDE.md`
- Usar formato conciso: tablas > párrafos, bullets > prosa

## Checklist pre-commit

- [ ] ¿Backend reiniciado si hubo cambios .py?
- [ ] ¿Migraciones con `migrate_schemas`, no `migrate`?
- [ ] ¿ViewSets tienen `queryset` class-level?
- [ ] ¿Permisos correctos en el ViewSet?
- [ ] ¿AuditViewSetMixin como primer parent?
- [ ] ¿PII cifrada si aplica?
- [ ] ¿Sin secretos en el código?
