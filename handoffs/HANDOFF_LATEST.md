# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).
> Actualizado: **2026-07-10**. El anterior está en
> `handoffs/history/HANDOFF_2026-07-08_c.md` (arranque de entorno + fix email + feat MFA super-admin).

## Resumen ejecutivo

Sesión de **features + QA + documentación** sobre el build ya feature-complete. Cinco tandas, todas
commiteadas y pusheadas a `origin/main`:

1. **Tests de la feature MFA** del super-admin (12 tests) — `test(mfa)`.
2. **CLAUDE.md** actualizado al estado real del proyecto — `docs`.
3. **Recuperación de contraseña self-service** en acceso y proveedores (+ correos transaccionales con
   plantilla HTML de marca) — `feat(auth)`.
4. **Mesa de Ayuda ocultada** (es cliente-only; el servicio externo no existe) + ISSUE-006 — `chore(soporte)`.
5. **Aviso de privacidad + Términos** sembrados por defecto al crear tenant, con backfill para los
   existentes — `feat(cumplimiento)`.

Además: **QA E2E** de 2 de 4 flujos (los automatizables), y aclaración del estado de **CI/CD**.

## Estado por módulo (cambios de esta sesión)

| Área | Estado | Notas |
|---|---|---|
| MFA super-admin | ✔ + tests | `tests/test_mfa_superadmin.py` (12). ⚠️ Ver "Contexto no obvio #1": el TOTP quedó **reseteado**. |
| Recuperación de contraseña | ✔ | `common/password_reset.py`: token firmado tenant-aware, por contexto, un solo uso, 1h. Vistas por contexto + 4 rutas. Páginas Recuperar/Restablecer + enlace en login (acceso y proveedores). 10 tests. |
| Correos transaccionales | ✔ | invitación/verificación/activación + reset ahora usan la plantilla de marca (`common/email_builder`) con fallback en texto plano. |
| Mesa de Ayuda (soporte) | ◑ | Cliente-only; ítem de menú oculto (reversible). Servicio externo pendiente. KNOWN_ISSUES ISSUE-006. |
| Documentos legales | ✔ | `apps/cumplimiento/documentos_default.py`: aviso + términos v1 (plantillas en texto plano, LFPDPPP) sembrados en el provisioning. Command backfill `sembrar_documentos_legales`. Ya corrido contra `museos`. 4 tests. |
| CI | ✔ (ya existía) | `.github/workflows/ci.yml`: ruff + pytest completo + build de las 4 SPAs en push a `main` y PRs. |
| CD (deploy) | 🔲 | **Pendiente**: no hay destino de producción decidido aún. No empezar hasta definir host. |

## Cambios de esta sesión (commits en `origin/main`)

```
8723241 feat(cumplimiento): sembrar aviso de privacidad y términos por defecto
2231252 chore(soporte): ocultar Mesa de Ayuda y documentar ISSUE-006
1c25522 feat(auth): recuperación de contraseña self-service en acceso y proveedores
2f94117 docs: actualizar CLAUDE.md al estado real del proyecto
5acaa02 test(mfa): cobertura de bootstrap_superadmin, login y activación TOTP
```

- **Tests:** 65 en la suite (última corrida sin aislamiento: 56/56 verdes; `ruff` limpio).
- **Builds:** las 4 SPAs compilan (`tsc && vite build`).

## Resultado del QA E2E (2026-07-10)

Método (A) = manejado por HTTP a través del stack real (nginx → backend → BD). Método (B) = requiere
clicks en navegador (no automatizable desde la sesión).

| # | Flujo | Método | Resultado |
|---|---|---|---|
| 1 | Recuperación de contraseña (acceso + proveedores) | A | ✅ **Completo**: solicitar (genérico) → confirmar → re-login; token de un solo uso; rechazo cross-context. Enlaces correctos (`/restablecer` y `/proveedores/restablecer`). |
| 4 | Documentos legales (aviso + términos) | A | ✅ **Completo**: servidos por el endpoint público (`/api/privacidad/documento/<tipo>/`), v1, nombre del tenant interpolado. |
| 2 | MFA super-admin (enrolar de cero) | B | ⏳ **Pendiente de clicks**: TOTP reseteado y listo; falta loguear en `admin.localhost:8080` y escanear el QR. |
| 3 | Onboarding nuevo tenant | mixto | ⏳ **Pendiente**: falta registrarse en `xenty.localhost:8080` con un correo real. |

## Contexto NO obvio (IMPORTANTE)

1. **El TOTP del super-admin está RESETEADO** (a propósito, para el QA de enrolamiento que quedó
   pendiente): `admin@xenty.mx` tiene `mfa_habilitado=True` y `mfa_totp_secret=None`. **El primer
   login en `admin.localhost:8080` mostrará un QR nuevo** para enrolar. Si se quiere volver al estado
   anterior sin enrolar por UI, hay que generar un secreto por API. No es un bug: es estado de QA.
2. **Correo = Gmail real** (`.env`: `smtp.gmail.com:587`). Los correos de reset/verificación salen al
   buzón real del destinatario. Mailpit sigue arriba pero no se usa. Para QA offline de correo,
   cambiar `.env` a Mailpit (`EMAIL_HOST=mailpit`, `EMAIL_PORT=1025`, `EMAIL_USE_TLS=False`) y
   `--force-recreate` del backend.
3. **Recuperación de contraseña — endpoints** (data plane, por subdominio de tenant):
   `POST /api/auth/{acceso|proveedores}/password/solicitar/` y `.../confirmar/`. `solicitar` responde
   **siempre** genérico (sin enumeración). El enlace apunta al SPA: acceso → `{host}/restablecer`,
   proveedores → `{host}/proveedores/restablecer`.
4. **Documentos legales por defecto**: se siembran en `provisionar_tenant` (aplica a CLI y signup).
   Para **tenants ya existentes** hay que correr una vez el backfill:
   `python manage.py sembrar_documentos_legales` (idempotente; `--schema <slug>` para uno solo).
   **Pendiente correrlo en staging/prod.**
5. **Mesa de Ayuda** (`apps.soporte`) es **cliente-only**: no existe el servicio externo (Nivel B).
   `mesa.xenty.mx` es solo placeholder. Ítem de menú oculto en `frontend-acceso/Layout.tsx` (la ruta
   `/soporte` y `/api/soporte/*` siguen activos). Reactivar = descomentar. Ver ISSUE-006.
6. **CI ya existe** (`.github/workflows/ci.yml`) y corre en cada push/PR. Lo que falta es **CD**, que
   necesita destino de producción (VPS/PaaS/K8s), registro de imágenes y estrategia de rama. No
   arrancar el CD hasta definir el host.

## Próximos pasos sugeridos

1. **Cerrar el QA E2E interactivo** (#2 MFA super-admin, #3 onboarding) en el navegador.
2. **Decidir el destino de producción** → armar **CD** (workflow de deploy + `nginx` prod + serving
   de `/media` con policy de pertenencia + secrets).
3. **Backfill de documentos legales** en staging/prod cuando existan (`sembrar_documentos_legales`).
4. No bloqueantes: MFA obligatorio para `Usuario`/`CuentaProveedor` del tenant; hardening de logs PII
   (structlog); UX del 403 de email no verificado en `frontend-acceso`; construir el servicio externo
   de Mesa de Ayuda (ISSUE-006).

## Verificar servicios

```bash
docker compose ps                                            # 13 Up
docker compose exec backend pip install -r requirements-dev.txt   # una vez (pytest no está en la imagen)
docker compose exec backend python -m pytest -q --ignore=tests/test_aislamiento_tenants.py
# QA de recuperación de contraseña (stack real): ver los flujos en el handoff / historial de la sesión.
docker compose exec backend python manage.py sembrar_documentos_legales --schema <slug>   # backfill legal
```
