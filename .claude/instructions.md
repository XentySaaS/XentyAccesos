# Instrucciones para Claude — Xenty Acceso

## Al iniciar sesión

1. Lee `CLAUDE.md` (reglas operativas, stack, convenciones)
2. Lee `handoffs/HANDOFF_LATEST.md` (estado actual, issues, próximos pasos)
3. Si necesitas más contexto: `docs/STATUS.md`, `docs/KNOWN_ISSUES.md`
4. NO leas toda la carpeta `docs/` — solo lo que necesites para la tarea

## Reglas permanentes

- No romper compatibilidad con el esquema de base de datos existente
- No portar deuda del repo Laravel viejo — reimplementar limpio
- No inventar alcance fuera de la fase actual del playbook
- Documentar decisiones importantes en `docs/DECISIONS.md`
- Mantener `CLAUDE.md` como fuente de verdad operativa
- Priorizar seguridad: PII cifrada, Fernet QR, sin secretos en repo
- Evitar duplicación de código y abstracciones prematuras
- No generar código innecesario ni features no solicitadas

## Operaciones críticas

- **Migraciones**: SIEMPRE `migrate_schemas --shared` y `--tenant`. NUNCA `migrate` a secas.
- **Backend restart**: `docker compose restart backend` después de cada cambio `.py` (usa `--noreload`)
- **ViewSets con get_queryset()**: mantener `queryset = Model.objects.none()` como class attr
- **HistorialCambio.usuario**: solo acepta `accounts.Usuario`. CuentaProveedor → `None`
- **Celery + tenant**: toda task envuelta en `tenant_context(tenant)`
- **Archivos subidos**: validar extensión + MIME + tamaño. Nombre lo pone el servidor.
- **PII**: cifrar con Fernet (ine_data, curp, nss). Disco privado por schema.

## Lo que NO hacer

- No usar `migrate` sin `_schemas`
- No pasar `CuentaProveedor` como `usuario` a `HistorialCambio`
- No crear ViewSet sin `queryset` class-level si usas `get_queryset()`
- No agregar endpoints de mantenimiento (`/migrate`, `/clear-cache`)
- No commitear `.env`, secretos o credenciales
- No editar migraciones ya aplicadas — crear nuevas
- No borrar empleados/usuarios físicamente — baja lógica (`activo=False`)
- No duplicar info de CLAUDE.md en otros archivos — referenciar

## Actualizar documentación

Después de cada tarea significativa:
1. `docs/STATUS.md` si cambió estado de un módulo
2. `docs/CHANGELOG.md` con los cambios realizados
3. `docs/DECISIONS.md` si hubo decisión técnica
4. `docs/KNOWN_ISSUES.md` si se encontró o resolvió un issue
5. `handoffs/HANDOFF_LATEST.md` al final de la sesión

## Regla crítica: verificar antes de documentar estado

**Nunca marques un módulo como "stub", "pendiente" o "no iniciado" sin leer su código real**
(`wc -l`, `grep` de funciones clave, o `Read` del archivo). El 2026-07-02, una pasada de
documentación marcó `dispositivos`, `mensajeria` y `cumplimiento` como no iniciados/stub basándose
en el nombre de la carpeta y memoria de sesión — los tres tenían backend funcional (HMAC edge auth,
retry queues de Celery, servicios completos). Se corrigió tras verificar con `Read`/`Grep`.

Antes de escribir en `docs/STATUS.md`, `docs/ROADMAP.md` o `handoffs/HANDOFF_LATEST.md` que algo
"no existe" o "es un stub": abre el archivo. Si un subagente reporta el estado de un módulo,
verifica su conclusión con al menos un `Read` o `Grep` propio antes de propagarla a la documentación
persistente — los subagentes pueden ser interrumpidos (rate limits, timeouts) y rellenar huecos con
suposiciones plausibles pero falsas.
