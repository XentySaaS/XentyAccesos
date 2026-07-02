# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).

## Resumen ejecutivo

Xenty Acceso es un SaaS multitenant de control de accesos a recintos, reconstruido desde Laravel a Django+React. Las fases F0–F7 tienen backend completo (auth, CRUD, eventos, citas, acceso, dispositivos edge, mensajería, cumplimiento). Falta UI de cumplimiento, frontend-admin completo, tests de aislamiento, y confirmar cobertura real del ETL F8.

## Estado por módulo (verificado leyendo código — ver `docs/STATUS.md` para detalle completo)

| Módulo | Estado | Notas |
|---|---|---|
| tenants + auth (F0) | ✔ | JWT dual (acceso/proveedores), Argon2id, MFA TOTP |
| accounts (F1) | ✔ | CRUD usuarios, roles, PermisoUsuario granular |
| proveedores (F1) | ✔ | Login, onboarding, CuentaProveedor |
| empleados (F1) | ✔ | CRUD, import Excel, foto, documentos |
| recintos (F1) | ✔ | Topología completa |
| documentos (F2) | ✔ | TipoDocumento, verificación |
| eventos (F3) | ✔ | CRUD + gafete QR Premium Dark |
| citas (F4) | ✔ | CRUD + gafete adaptativo + email |
| acceso (F5) | ✔ | Scanner QR, bitácora |
| sanciones (F5) | ✔ | CRUD |
| gafetes | ✔ | Fernet QR, diseño Premium Dark |
| dispositivos (F6) | ✔ | EdgeHMACAuthentication + nonce anti-replay (Redis) |
| mensajeria (F7) | ✔ | Backend + retry Celery (`enviar_campana`, max_retries=3) + UI |
| cumplimiento (F7) | ⚠ | Backend completo (`importar_efos_task` con retry); **sin UI** |
| config/reportes (F8) | ⚠ | DashboardView/CalendarioView/ExportarAccesosView existen; ETL scaffold (`etl/transformers.py` 63L, `migrar_tenant_sar` 64L) sin auditar cobertura |
| soporte | ⚠ | Mesa de Ayuda stub |
| frontend-acceso | ✔ | Todas las pantallas operativas excepto cumplimiento |
| frontend-proveedores | ✔ | Onboarding, empleados, docs, eventos |
| frontend-admin | ⚠ | Solo Login + lista Tenants |
| tests | ⚠ | `tests/test_f0_modelos.py` (58L) existe; falta suite `-k aislamiento` obligatoria |

> **Nota de fases:** la numeración F0–F8 es la de `docs/PLAYBOOK_SAR_XENTY.md`, NO la que aparecía
> en handoffs previos de esta sesión (esa numeración estaba inventada). "Roles/permisos granulares"
> no es una fase — es una mejora transversal sobre F1/accounts.

## Última sesión (2026-07-02)

- **Roles/permisos**: RequiereRol en todos los ViewSets + PermisoUsuario (modelo, migración 0005, serializer, action GET/PUT, modal UI)
- **Fix AuditViewSetMixin**: `registrar()` crasheaba con `ValueError` cuando `request.user` era `CuentaProveedor` → isinstance check, pasa `usuario=None`
- **Fix CitaViewSet**: `queryset = Cita.objects.none()` — DRF router necesita class-level queryset para inferir basename
- **Fix FotoCirculo**: `useEffect(() => setErr(false), [foto])` — React no resetea error de `<img>` al cambiar src
- **Gafete citas sin foto**: layout adaptativo — sin recuadro de foto, zona ocupa ancho completo, Bebas 58px, PZ_H=114
- **Citas services**: pasa `foto_bytes` del empleado vinculado si `tipo=EMPLEADO`

## Archivos modificados (última sesión)

- `backend/apps/config/services.py` — isinstance check en registrar()
- `backend/apps/accounts/models.py` — PermisoUsuario model
- `backend/apps/accounts/views.py` — action permisos GET/PUT
- `backend/apps/accounts/serializers.py` — PermisoUsuarioSerializer
- `backend/apps/accounts/migrations/0005_permisousuario.py`
- `backend/common/permissions.py` — RequierePermisoPersonalizado()
- `backend/apps/citas/views.py` — queryset=none(), get_queryset ownership
- `backend/apps/gafetes/services.py` — layout sin foto, silueta mejorada
- `backend/apps/citas/services.py` — foto_bytes de empleado en gafete
- `backend/apps/eventos/views.py` — RequiereRol + PermisoPersonalizado
- `backend/apps/acceso/views.py` — roles actualizados
- `backend/apps/mensajeria/views.py` — roles actualizados
- `backend/apps/sanciones/views.py` — roles actualizados
- `backend/apps/recintos/views.py` — roles actualizados
- `frontend-acceso/src/pages/Usuarios.tsx` — modal permisos
- `frontend-acceso/src/components/Layout.tsx` — NAV_ITEMS filtrado por rol
- `frontend-proveedores/src/pages/Empleados.tsx` — FotoCirculo fix, feedback foto

## Contexto no obvio

1. **DRF Router + queryset**: ViewSets con `get_queryset()` NECESITAN `queryset = Model.objects.none()` como atributo de clase. Sin esto, crash en startup.
2. **HistorialCambio.usuario**: FK solo acepta `accounts.Usuario`. CuentaProveedor pasa `None` (campo nullable). Fix en `config/services.py:registrar()`.
3. **Backend --noreload**: cada cambio `.py` requiere `docker compose restart backend`.
4. **JWT ctx claim**: `"acceso"` o `"proveedores"` — separación de actores.
5. **Migraciones**: SIEMPRE `migrate_schemas --shared` / `--tenant`. NUNCA `migrate` a secas.
6. **Acceso dev**: vía Nginx `tenant.localhost:8080`, NO puertos Vite directos.

## Issues abiertos

1. Subida de foto empleado — confirmar fix de ValueError end-to-end
2. Nginx `/media/` — verificar que sirve archivos en dev

## Próximos pasos

1. Verificar foto empleado funciona end-to-end
2. Confirmar Nginx sirve `/media/`
3. Tests pytest (suite aislamiento obligatoria — bloquea confianza en el resto)
4. Pantalla frontend de cumplimiento SAT 69-B (backend ya existe)
5. Auditar cobertura real del ETL F8 contra `docs/MIGRACION_DATOS_SAR.md`

## Verificar backend

```bash
docker compose ps backend  # debe estar Up
docker compose logs --tail=5 backend  # "Starting development server"
```
