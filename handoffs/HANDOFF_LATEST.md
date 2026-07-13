# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual) → `docs/STATUS.md`
> (estado vivo por módulo).
> Actualizado: **2026-07-13**. El anterior (2026-07-10: tests MFA, recuperación de contraseña,
> Mesa de Ayuda oculta, documentos legales) está en `handoffs/history/HANDOFF_2026-07-10.md`.

---

## Resumen ejecutivo

Sesión de **hardening + una feature de operación + documentación**. Cinco commits, todos en
`origin/main`, árbol limpio:

1. **`f5bfd00`** `style` — `ruff format` sobre 5 archivos que rompían CI (`ruff format --check`).
2. **`d206995`** `chore(dev)` — **pre-commit hook** con ruff (format + check --fix) vía Docker, para
   que el formato no vuelva a romper CI.
3. **`9779985`** `fix(mfa)` — **el secreto TOTP ya no se persiste hasta confirmar el enrolamiento**
   (arreglo del bug del QR que "desaparecía"). Ahora vive en cache hasta activar.
4. **`c85110f`** `docs` — seguimiento del **Connector (XCC)** en `docs/STATUS.md` (fases F-C/F-D/F-E +
   decisión pendiente de proveedor de WhatsApp).
5. **`90e031b`** `feat(admin)` — el super-admin puede **reenviar** o **verificar manualmente** el
   correo del administrador de un tenant cuando el doble opt-in no llega.

**Suite completa: 68/68 verdes** (última corrida, ~104 s). `ruff` limpio. Las 4 SPAs compilan.

---

## Cambios de esta sesión (commits en `origin/main`)

```
90e031b feat(admin): reenviar y verificar manualmente el correo del admin del tenant
c85110f docs: seguimiento del Connector (XCC) en STATUS + refresco de próximos objetivos
9779985 fix(mfa): no persistir el secreto TOTP hasta confirmar el enrolamiento
d206995 chore(dev): pre-commit hook con ruff (format + check --fix) via docker
f5bfd00 style: aplicar ruff format (arregla CI: ruff format --check)
```

## Estado por área (cambios de esta sesión)

| Área | Estado | Notas |
|---|---|---|
| MFA (enrolamiento TOTP) | ✔ arreglado | El secreto se guarda **en cache** (`_ENROL_TTL=600s`), no en BD, hasta que `ActivarTOTPView` confirma el 1er código. Un enrolamiento abandonado ya no deja al actor "a medio enrolar". `common/mfa_api.py`. **QA #2 cerrado** (el super-admin completó el enrolamiento y entró al dashboard). |
| Verificación de correo del admin (super-admin) | ✔ + tests | 3 acciones nuevas en `TenantAdminViewSet` (control plane) que entran al schema del tenant. Tarjeta en `frontend-admin/TenantDetalle.tsx`. Red de seguridad para el onboarding si el correo no llega. |
| Pre-commit hook | ✔ | `.githooks/pre-commit`: corre `ruff format` + `ruff check --fix` sobre los `.py` staged de `backend/` dentro del contenedor, re-stagea, y bloquea si queda lint no auto-corregible. Activar: `git config core.hooksPath .githooks`. |
| CI | ✔ (verde) | Se arregló la corrida roja de `ruff format --check`. El hook previene recurrencia. |
| Connector (XCC) | doc | Estado real ahora documentado en STATUS (F-D implementado + con tests; F-C en repo `xenty-connector`; F-E pendiente). |

---

## Feature nueva: verificación de correo del admin del tenant (detalle)

**Problema que resuelve:** en el alta pública (`SignupView`, `verificar_email=False`) el admin del
tenant queda con doble opt-in pendiente. Si el correo no llega (spam, typo, SMTP), queda **bloqueado
por el permiso DRF `EmailVerificado`** y no puede operar. El super-admin ahora lo destraba desde el
control plane.

**Backend — `backend/apps/tenants/admin_api.py`, `TenantAdminViewSet`** (3 `@action` detail):

| Acción | Método · ruta | Qué hace |
|---|---|---|
| `verificacion` | `GET .../verificacion/` | Lista los administradores del tenant y su estado (`verificado: bool`). |
| `reenviar_verificacion` | `POST .../reenviar-verificacion/` | Reenvía el correo de verificación (plantilla de marca) a los admins pendientes. |
| `verificar_email` | `POST .../verificar-email/` | Marca `email_verificado = now()` a los pendientes (fallback sin correo). Registra en `HistorialCambio` (con `usuario=None`, porque el actor es super-admin del control plane, no un `Usuario` del tenant). |

- Helper `_admins(tenant, solo_pendientes=)` filtra `Usuario.objects.filter(rol=ADMINISTRADOR,
  activo=True)`; con `solo_pendientes` añade `email_verificado__isnull=True`.
- **Las 3 acciones entran a `schema_context(tenant.schema_name)`** porque `accounts.Usuario` vive en
  el schema del tenant, no en `public`. Los permisos siguen siendo `IsAuthenticated + MFASesionCompleta
  + EsSuperAdmin`.
- Ambas acciones POST son **idempotentes**: si no hay pendientes responden 200 con lista vacía.

**Frontend — `frontend-admin/src/pages/TenantDetalle.tsx`:** tarjeta "Verificación de correo del
administrador" con la lista de estado + botones **Reenviar verificación** y **Verificar manualmente**.

**Tests — `backend/tests/test_tenant_verificacion_admin.py`** (3): lista pendiente, reenvío (usa
`mailoutbox`, valida `alternatives` = plantilla HTML), y verificación manual idempotente. Fixture
`tenant_sin_verificar` **module-scoped** (provisiona con `verificar_email=False`; drop de schema en
teardown).

---

## Contexto NO obvio (IMPORTANTE)

1. **El fix de MFA cambió el modelo del handoff anterior.** Ya **no** hay "TOTP reseteado a propósito":
   el enrolamiento es ahora **basado en cache**. `EnrolarTOTPView` genera el secreto y lo guarda en
   cache bajo `mfa:totp:enrol:{ctx}:{schema}:{user.pk}` (TTL 600s), **sin tocar la BD**;
   `ActivarTOTPView` lo lee de cache, verifica el 1er código y **recién ahí** persiste
   `mfa_totp_secret` + `mfa_habilitado=True`. Recargar el QR reutiliza el secreto en curso (no
   invalida el que ya escaneaste). El super-admin `admin@xenty.mx` **ya completó** su enrolamiento.
2. **Correo = Gmail real** (`.env`: `smtp.gmail.com:587`). Reenvíos de verificación salen al buzón real.
   Para QA offline: `.env` → Mailpit (`EMAIL_HOST=mailpit`, `EMAIL_PORT=1025`, `EMAIL_USE_TLS=False`) y
   `docker compose up -d --force-recreate backend`.
3. **Pre-commit hook**: no se activa solo tras `clone`. Cada quien corre una vez
   `git config core.hooksPath .githooks`. Necesita el contenedor `backend` **arriba** (usa
   `docker compose exec`); si Docker está apagado, el hook lo avisa y no bloquea el commit.
4. **`verificar-email` (manual) es un bypass del doble opt-in**: úsalo solo como fallback cuando el
   correo genuinamente no llega. Queda auditado en `HistorialCambio` del tenant.
5. **Connector (XCC)**: `apps/mensajeria` ya tiene el enchufe `connector_provider.py` + Router con
   failover (F-D, con tests). El **servicio** XCC vive en el repo separado `xenty-connector` (Node +
   Baileys). Falta **F-E** (nonce en Redis, repo remoto del connector, deploy) y **decidir el proveedor
   de WhatsApp** (ver abajo).
6. **CI ya existe**; falta **CD** (sin host de producción decidido — no arrancar hasta definirlo).

---

## Decisiones abiertas (requieren al usuario)

1. **Proveedor de WhatsApp** — hoy **UltraMsg** primario (~$39/mes, no-oficial). Opciones:
   (a) promover **XCC/Baileys** a primario (self-host, ~$0 + servidor, mismo riesgo de baneo), o
   (b) añadir **WhatsApp Cloud API oficial** (Meta, pago por conversación, sin baneo, requiere
   plantillas). El Router con failover ya soporta ambos caminos. Documentado en `docs/STATUS.md`.
2. **Destino de producción / CD** — bloqueado hasta elegir host (VPS/PaaS/K8s).

## QA E2E — estado

| # | Flujo | Resultado |
|---|---|---|
| 1 | Recuperación de contraseña (acceso + proveedores) | ✅ Completo (2026-07-10, stack real) |
| 2 | MFA super-admin (enrolar de cero) | ✅ **Completo** (usuario enroló y entró al dashboard) |
| 4 | Documentos legales (aviso + términos) | ✅ Completo (2026-07-10, endpoint público) |
| 3 | Onboarding nuevo tenant | ⏳ **Pendiente de clicks**: registrarse en `xenty.localhost:8080` con correo real. Si el correo no llega → destrabar con la feature nueva en `admin.localhost:8080` (Reenviar / Verificar manualmente). |

## Próximos pasos sugeridos

1. **Cerrar QA #3 (onboarding)** en el navegador — ya con la red de seguridad de verificación manual.
2. **Resolver el proveedor de WhatsApp** y cerrar **F-E** del Connector (nonce Redis, repo remoto, deploy XCC).
3. **Definir host de producción → armar CD** (workflow deploy + nginx prod + serving `/media` con policy + secrets).
4. **Backfill de documentos legales** en staging/prod cuando existan (`python manage.py sembrar_documentos_legales`).
5. No bloqueantes: MFA obligatorio para `Usuario`/`CuentaProveedor` del tenant; hardening de logs PII
   (structlog); servicio externo de Mesa de Ayuda (ISSUE-006).

## Verificar servicios

```bash
docker compose ps                                                 # core Up
docker compose exec backend pip install -r requirements-dev.txt   # una vez (pytest no está en la imagen prod)
docker compose exec backend python -m pytest -q --ignore=tests/test_aislamiento_tenants.py
git config core.hooksPath .githooks                               # activar el pre-commit hook (una vez)
docker compose exec backend python manage.py sembrar_documentos_legales --schema <slug>   # backfill legal
```
