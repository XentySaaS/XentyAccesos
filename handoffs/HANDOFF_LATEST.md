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

> **Continuación (misma fecha):** se retomó el **Connector (XCC)** y se **completó F-E (código)**: nonce
> en Redis, repo remoto, métricas Prometheus, webhook de estados, routing sticky / propiedad de sesión,
> `connection_id` por tenant y artefactos de deploy. Solo falta provisionar el XCC en un host. Ver la
> sección "Connector (XCC) — F-E" abajo.

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

## Connector (XCC) — F-E (repo `xenty-connector`)

> El Connector vive en un **repo separado**: `C:\Users\ADMIN\Documents\ProyectosElevation\xenty-connector`
> (Node 20 + TS + Fastify + Baileys). El repo principal NO depende de él (failover a UltraMsg/Sandbox).

**Qué se hizo** (commit `cd2c85e` en `xenty-connector`, ya pusheado a
`github.com/ElevationStudioMX/XentyC`):
- El anti-replay pasó de un `Map` en proceso a una **interfaz `NonceStore`** con dos implementaciones
  elegidas por `XCC_REDIS_URL`:
  - `InMemoryNonceStore` — comportamiento actual (una sola instancia).
  - `RedisNonceStore` — `SET NX PX` **atómico** compartido → permite desplegar **varias réplicas** del
    Connector sin aceptar replays entre ellas. Es el desbloqueo de la escala horizontal de F-E.
- `seen()` puede ser sync (memoria) o async (Redis); `auth.ts` hace `await`. **Fail-closed**: si Redis
  no responde, `seen()` lanza `NonceStoreUnavailableError` y `/v1` responde **503** (el Router del
  principal hace failover) en vez de arriesgar un replay. `commandTimeout=2000ms` acota la espera; se
  deja la cola offline (default) para no fallar durante la ventana de conexión inicial.
- `docker-compose.yml` del connector ahora incluye **su propio Redis** (sin persistencia: los nonces
  son efímeros), cableado por defecto (`XCC_REDIS_URL=redis://redis:6379` con override).
  `.env.example` documenta la variable (vacío = in-memory).

**Métricas Prometheus** (connector `b3f2f04`): `GET /metrics` (prom-client) con
`xcc_messages_total{tenant,type,result}`, `xcc_message_send_duration_seconds`, `xcc_sessions{state}`
(gauge calculado por scrape) + métricas del proceso Node. Sin auth por defecto; `XCC_METRICS_TOKEN`
opcional exige `Authorization: Bearer`.

**Webhook de estados de entrega** (connector `b3f2f04` emite + principal `ade929e` recibe):
- Connector: `SessionManager` engancha `messages.update` de Baileys, mapea el status numérico a
  `delivered/read/failed` y hace `POST` firmado HMAC (mismo esquema que `/v1`) a `XCC_WEBHOOK_URL`
  (opcional; sin la var no emite nada). Correlación por `message_id`. Best-effort.
- Principal: `POST /api/mensajeria/connector/webhook/` (control plane, `urls_public`), verifica
  HMAC+ventana+nonce (cache Redis) y actualiza `DestinatarioMensaje` por `external_id`. `Estado` gana
  `entregado`/`leido` (**migración `mensajeria.0005`** — ya aplicada al DB dev). **Solo avanza** el
  estado (delivered tardío no pisa read). Endpoint idempotente.

**Routing sticky / propiedad de sesión** (connector `f720b20`): con varias réplicas, cada sesión
`(tenant, connection_id)` tiene **un único dueño** (lock Redis `SET NX` + heartbeat, clave
`xcc:owner:{tenant}:{connection_id}`); `sendMessage` a un no-dueño → `409 { owner }`. El
`ConnectorProvider` del principal envía `X-XCC-Connection` para el hash consistente del ingress. Sin
Redis = una sola instancia (sin cambios). Config: `XCC_INSTANCE_ID`, `XCC_OWNER_TTL_SEC`.

**`connection_id` configurable por tenant** (principal `e67e382`): `PreferenciaMensajeria.connection_id`
(**migración 0006**), el Router instancia el `xcc` con él; API + pantalla "Mensajería · Proveedores"
lo exponen (campo con Ayuda, validado).

**Deploy** (connector `cbf89dc`, `1634a0f`): **artefactos listos** — `DEPLOY.md` (runbook),
`docker-compose.prod.yml` (puerto en loopback tras reverse proxy, redis, restart always) y
`nginx.xcc.conf.example` (TLS + `/metrics` restringido + upstream con hash por `connection_id`).
**Decisión DEC-008:** el XCC va en el **mismo CD** que el principal pero como **servicio opcional
(opt-in)**; en prod puede no levantarse y su ausencia no afecta al principal (master switch + failover).
**Verificado end-to-end en host local (staging, 2026-07-13):** `docker compose -f docker-compose.prod.yml
up` → connector + redis healthy; arranque con nonce+ownership en Redis; contrato HMAC vivo
(unsigned→401, firmado→200, replay→401, `/metrics` con token). **Interop bidireccional**: main→XCC
(`ConnectorProvider` firma OK → XCC responde 409 por sesión no escaneada) y XCC→webhook del principal
(endpoint vivo, exige HMAC → 401). El `ConfiguracionConnector` del dev quedó apuntando al XCC local
(`host.docker.internal:8090`, master switch ON) — no afecta a los tenants salvo que agreguen `xcc` a su
orden de proveedores. **Falta solo provisionar en un host de producción** (mismo bloqueo que el CD del
principal). Para stop: `docker compose -f docker-compose.prod.yml down` en `xenty-connector`.

**Pantallas de vinculación de WhatsApp** (principal `6a10439`): los usuarios ya **no necesitan CLI**
para vincular el número. El navegador nunca ve el secreto HMAC — el backend firma por él
(`apps/mensajeria/connector_client.py`, reusa la firma de `ConnectorProvider`):
- **Admin del tenant** (frontend-acceso, *Mensajería · Proveedores*): tarjeta "WhatsApp del Connector"
  con estado, botón **Vincular** → QR con polling hasta conectar, y **Desvincular**. Endpoints
  `/api/mensajeria/whatsapp/sesion/` (GET/POST/DELETE) + `/qr/` (conexión = `PreferenciaMensajeria.connection_id`).
- **Super-admin** (frontend-admin, *Comunicaciones*): sección "Sesiones por tenant" (tenant + conn →
  vincular/estado/QR/desvincular). Endpoints `/api/admin/comunicaciones/sesion/` + `/qr/`.
- Tests: 5 (`test_connector_sesiones.py`). Verificado en vivo: el proxy firmado alcanzó el XCC local y
  devolvió la sesión de `museos` (200). Ambas SPAs compilan.

**XCC como servicio del compose del principal** (perfil `connector`, DEC-008): el XCC está en
`docker-compose.yml` del principal (build `../xenty-connector`, mismo network, comparte el redis del
stack). Se levanta con `docker compose --profile connector up -d --build connector`; `docker compose up`
normal lo ignora. En local la URL base en *Comunicaciones* es **`http://connector:8090`** (ya no
`host.docker.internal`). Requiere `XCC_HMAC_SECRET` en el `.env` del principal (= hmac_secret de
*Comunicaciones*). Verificado: proxy POST → 201 por la red interna.

**Dos gotchas de dev resueltos hoy:** (1) la URL base NO puede ser `127.0.0.1`/`localhost` (dentro del
contenedor apunta al backend, no al XCC) — con el perfil es `http://connector:8090`. (2) el `backend`/
`superadmin-backend` corren con `runserver --noreload`: **tras agregar rutas/vistas hay que
`docker compose restart backend superadmin-backend`** o la UI da 404 aunque el código esté bien.

**Verificación:**
- **Connector** (contenedor `node:20-slim`, Node no está en el host): `typecheck` + `build` limpios;
  `npm test` → **29 tests** (nonce/metrics/webhook/ownership/server); integración Redis (nonce +
  propiedad de sesión) verificada contra `redis:7-alpine` real.
- **Principal** (`docker compose exec backend pytest`): `test_connector_webhook.py` **5/5** +
  `test_connector_provider.py` **7/7** (incl. connection_id por tenant); suite sin aislamiento **64
  verdes**; migraciones `mensajeria.0005`/`0006` aplicadas; `ruff` limpio (pre-commit OK).

**Cómo correr el connector** (recordatorio; Node solo vía Docker en esta máquina):
```bash
cd ../xenty-connector
docker run --rm -v "$PWD:/app" -w /app node:20-slim sh -c "npm install && npm test && npm run build"
# integración Redis: red docker + redis:7-alpine + -e XCC_TEST_REDIS_URL=redis://<host>:6379
cp .env.example .env   # define XCC_HMAC_SECRET; docker compose up levanta connector + redis
```

## Contexto NO obvio (IMPORTANTE)

0. **El repo `xenty-connector` ya tiene remoto** (resuelto 2026-07-13):
   `https://github.com/ElevationStudioMX/XentyC.git` (org **ElevationStudioMX**, distinta del principal
   en `XentySaaS/XentyAccesos`). `main` sigue a `origin/main`; ambos commits pusheados (`4d0e592` MVP +
   `cd2c85e` nonce Redis). Identidad git local del repo: `ChuyHR <manuel@elevation.com.mx>`.

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
2. **Connector F-E: código completo** (nonce Redis, repo remoto, métricas, webhook de estados, routing
   sticky, `connection_id` por tenant, artefactos de deploy). Falta **provisionar el XCC en un host**
   (ver `xenty-connector/DEPLOY.md`; bloqueado con el CD del principal) y **resolver el proveedor de
   WhatsApp** (UltraMsg vs XCC-primario vs Cloud API).
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
