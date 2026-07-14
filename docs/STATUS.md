# Estado del Proyecto — Xenty Acceso

> Actualizado: 2026-07-13 (ver `handoffs/HANDOFF_LATEST.md`)

## Backend

| App | Estado | Detalle |
|---|---|---|
| tenants | ✔ | Tenant, Domain, Plan, TenantMainMiddleware |
| accounts | ✔ | Usuario, PermisoUsuario, roles, JWT acceso |
| proveedores | ✔ | CuentaProveedor, Proveedor, onboarding, JWT proveedores |
| empleados | ✔ | CRUD, import Excel, foto (ImageField), docs |
| recintos | ✔ | Recinto, Zona, Acceso, Ubicacion, Entrada, AreaAutorizada, Protocolo |
| documentos | ✔ | TipoDocumento, DocumentoEmpleado, verificación estados |
| eventos | ✔ | Evento, EventoProveedor, asignación empleados, gafete QR. Invitación/asignación adjuntan **protocolo** y mandan gafete/pases por **WhatsApp** además del correo; cancelaciones con aviso dedicado |
| citas | ✔ | Cita, AsistenteCita, Contacto, EmpleadoCita. Invitación con **gafete + protocolo** adjuntos por correo **y WhatsApp** (redacción profesional); **cancelar** manda aviso de cancelación (no reenvía invitación). **Alta/baja de asistentes** en cita existente: agregar (invita solo a los nuevos, **dedup por email/teléfono**), dar de baja = **baja lógica** (estado CANCELADO; el escáner ya lo bloquea) + reactivar. **Cita cancelada = terminal** (no editar ni reenviar) |
| acceso | ✔ | RegistroAcceso, scanner QR, bitácora |
| gafetes | ✔ | componer_gafete (Premium Dark), estacionamiento, Fernet QR |
| sanciones | ✔ | Sancion CRUD |
| mensajeria | ✔ | MensajeWhatsApp, DestinatarioMensaje, Celery `enviar_campana` con retry. **Router con failover + circuit breaker** (`router.py`, `breaker.py`) sobre proveedores (`UltraMsg`, `Sandbox`, `xcc`) + preferencia por tenant. **Teléfonos: canónico 10 dígitos sin lada; la lada MX se antepone solo al enviar** (`common/phone.py`). **Adjuntos por WhatsApp** (gafete/protocolo) como media base64 (`AdjuntoWhatsApp`, texto primero + media best-effort). Ver §Connector |
| cumplimiento | ✔ | Backend (`importar_efos_task` con retry) + padrón EFOS global (`apps.efos`) + pantalla `Cumplimiento.tsx` en frontend-acceso |
| ocr | ✔ | Textract + sandbox para INE |
| config | ✔ | Opcion, HistorialCambio, AuditViewSetMixin, DashboardView, CalendarioView, ExportarAccesosView (F8) |
| soporte | ◑ | Mesa de Ayuda Nivel B: salud de config + cliente (probar/enviar, sandbox) + config por tenant + pantalla `Soporte.tsx`. **Cliente-only**: el servicio externo de Mesa aún no existe → ítem de menú **oculto temporalmente** (KNOWN_ISSUES ISSUE-006) |
| dispositivos | ✔ | `EdgeHMACAuthentication` con nonce anti-replay (Redis); `DispositivoEdge`/`ComandoEdge` en apps.tenants |

> **Correos (transversal):** plantilla unificada **«Xenty Accesos»** (oscura, por tablas) en
> `common/email_builder.py::construir_correo` — 6 tipos (`acceso`/`parking`/`recordatorio`/
> `modificacion`/`alerta`/`bienvenida`) + `info`, con hero + tarjeta de datos + mensaje + CTA. Todos los
> llamadores (citas, eventos, proveedores, documentos, reset/verificación) mapeados a su tipo.

## Frontends

| SPA | Estado | Detalle |
|---|---|---|
| frontend-acceso | ✔ | Auth, Dashboard, Usuarios+Permisos, Eventos, Citas, Acceso, Sanciones, Mensajería, Verificación |
| frontend-proveedores | ✔ | Auth, Onboarding, Dashboard, Empleados (foto+docs), MisEventos, Documentos |
| frontend-admin | ✔ | **Dashboard** + Tenants + **detalle de tenant** (asignar plan, billing/checkout Stripe, **créditos**, **periodo de gracia**) + **Planes CRUD** + **Seguridad/MFA TOTP** (login con paso MFA). Control plane funcionalmente completo |

## Infraestructura

| Componente | Estado |
|---|---|
| Docker Compose | ✔ Postgres 15 + Redis 7 + backend + Nginx |
| Celery worker/beat | ✔ Tasks activas: `enviar_campana` (mensajería), `importar_efos_task` (cumplimiento), ambas con retry |
| Nginx dev proxy | ✔ tenant.localhost:8080 |
| CI (GitHub Actions) | ✔ `.github/workflows/ci.yml`: ruff + pytest completo + build de las 4 SPAs en push a `main` y PRs |
| CD (deploy) | 🔲 Pendiente: sin destino de producción decidido (ver HANDOFF). El **XCC entra en el mismo CD como servicio opcional/opt-in** (DEC-008): puede no levantarse en prod sin afectar al principal |

## Connector de comunicaciones (XCC — WhatsApp)

> Diseño: `docs/ARQUITECTURA_CONNECTOR.md`. Repo del servicio: `xenty-connector` (Node + Baileys),
> **separado** del principal → `github.com/ElevationStudioMX/XentyC`. Es un **proveedor de WhatsApp de
> respaldo** self-hosted; el principal funciona igual si está apagado (failover a Sandbox/UltraMsg).

| Fase | Qué es | Estado |
|---|---|---|
| F-C | Servicio XCC (Node 20 + Fastify + **Baileys**): REST `/v1` + HMAC, sesiones por tenant, QR/pairing, media, persistencia, reconexión | ✔ MVP en repo `xenty-connector` (build en `dist/`, `.env.example`, Docker) |
| F-D | Enchufe al principal: `apps/mensajeria/connector_provider.py` (cliente REST+HMAC) + registro `xcc` en el Router con failover | ✔ Implementado y con tests (`tests/test_connector_provider.py`: firma, no-config, http≠202, **failover xcc→sandbox**) |
| F-E | Escala horizontal + observabilidad | ✔ código completo (falta solo provisioning en host): **nonce en Redis** (`cd2c85e`) · **repo remoto** (`github.com/ElevationStudioMX/XentyC`) · **métricas Prometheus** (`GET /metrics`, `b3f2f04`) · **webhook de estados** (connector `b3f2f04` + principal `ade929e`, actualiza `DestinatarioMensaje` por `external_id`, estados `entregado`/`leido` mig. 0005) · **routing sticky** (propiedad de sesión en Redis, `f720b20`; header `X-XCC-Connection`) · **`connection_id` por tenant** (`e67e382`, mig. 0006, UI) · **deploy** (artefactos `DEPLOY.md`+prod compose+nginx, `cbf89dc`; **verificado end-to-end en host local/staging** 2026-07-13: prod compose healthy, HMAC + nonce Redis + `/metrics` OK, interop bidireccional main↔XCC; falta **host de producción**) |

**Config runtime:** el super-admin activa/configura el Connector en la pantalla **Comunicaciones**
(`ConfiguracionConnector` global: `habilitado`, `url_base`, `hmac_secret` cifrado, umbrales del breaker).
El `hmac_secret` debe ser idéntico al `XCC_HMAC_SECRET` del servicio.

**Local (dev):** el XCC está en el `docker-compose.yml` del principal como servicio **opcional**
(perfil `connector`, DEC-008): `docker compose --profile connector up -d --build connector`. Queda en
la misma red → URL base en *Comunicaciones* = `http://connector:8090` (sin `host.docker.internal`).
Requiere `XCC_HMAC_SECRET` en el `.env` (igual al de *Comunicaciones*).

**Vinculación por UI (sin CLI):** el admin del tenant vincula su WhatsApp en *Mensajería · Proveedores*
(tarjeta "WhatsApp del Connector": estado + QR con polling + desvincular) y el super-admin gestiona
sesiones por tenant en *Comunicaciones*. El navegador **nunca** ve el secreto HMAC: el backend firma
por él (`apps/mensajeria/connector_client.py` → `/api/mensajeria/whatsapp/*` y
`/api/admin/comunicaciones/sesion|qr`).

**Decisión pendiente — proveedor de WhatsApp (costos):** hoy **UltraMsg** es el primario (~$39/mes,
no-oficial). XCC (Baileys, self-host) es **más barato** (~$0 + servidor) pero también **no-oficial**
(mismo riesgo de baneo). La **WhatsApp Cloud API oficial** (Meta) no tiene cuota fija (pago por
conversación) y evita baneos, a cambio de setup de plantillas. Opciones a evaluar: (a) promover XCC a
primario para quitar la mensualidad, (b) añadir Cloud API como primario oficial dejando XCC/UltraMsg
de respaldo. El Router con failover ya soporta ambos caminos.

## Seguridad

| Ítem | Estado |
|---|---|
| Argon2id passwords | ✔ |
| JWT blacklist + rotación | ✔ |
| Fernet QR (jti+exp+tenant) | ✔ |
| PII cifrada (ine_data, curp) | ✔ |
| Rate limiting | ✔ Login (10/m/IP), signup, onboarding, edge, ocr; `Ratelimited`→429 (handler DRF). Verificado en runtime (11º login → 429) |
| MFA TOTP | ✔ Enrolamiento + activación + verificación (super-admin con MFA obligatorio + tests) |
| WebAuthn | ✔ Registro/login por passkey (data plane + control plane) |
| Recuperación de contraseña | ✔ Self-service en acceso y proveedores (token firmado, un solo uso, 1h). QA E2E ✅ |
| Documentos legales por defecto | ✔ Aviso de privacidad + términos sembrados al crear tenant (+ command backfill) |

## Pendientes críticos

1. ✔ ~~Tests pytest — suite de aislamiento entre tenants~~ **HECHO (2026-07-02)**: `tests/test_aislamiento_tenants.py` (8 tests, todos verdes) + fixture `dos_tenants` en `tests/conftest.py`. Corre con `pytest -k aislamiento`. Cubre: fuga de datos por tenant (Usuario/Proveedor), padrón EFOS global visible desde todos, resultados 69-B por tenant, cache y storage segregados por schema, y ausencia estructural de tablas de tenant en `public`.
2. ✔ ~~Pantalla de cumplimiento SAT 69-B en frontend-acceso~~ **YA EXISTE**: `frontend-acceso/src/pages/Cumplimiento.tsx` (162 líneas), cableada en Layout/Dashboard/router/Proveedores.
3. ✔ ~~Verificar `/media/` en dev~~ **HECHO (2026-07-03)**: en dev se sirve `/media` solo para no-sensibles (fotos); INE/REPSE/SUA/docs bloqueados (se bajan por endpoint autenticado). Pendiente **deploy**: estrategia de serving de fotos en prod (hoy `/media` no lo sirve Django con `DEBUG=False`).

> **Correr los tests:** la imagen backend solo instala `requirements.txt` (prod, sin dev-tools por
> diseño). Instalar las dev-deps una vez en el contenedor: `docker compose exec backend pip install
> -r requirements-dev.txt`, luego `docker compose exec backend python -m pytest -k aislamiento`.
> (Nota: crear cada schema de tenant corre todas las migraciones → la suite tarda ~2.5 min.)

## Bloqueadores

Ninguno activo.

## Próximos objetivos

> **ETL/migración descartados**: el sistema original solo tuvo datos de prueba → no hay migración.
> Este build es la implementación final (go-live con tenants nuevos vía onboarding self-service).

1. **CD / deploy a producción** (Nginx prod, secrets, serving de `/media`) — falta decidir el host. CI ya existe.
2. **Connector/WhatsApp**: **F-E código completo** (nonce Redis, repo remoto, métricas, webhook de estados, routing sticky, `connection_id` por tenant, artefactos de deploy). Falta **provisionar el XCC en un host** (bloqueado con el CD del principal) y **resolver la decisión de proveedor** (XCC-primario vs Cloud API oficial vs seguir con UltraMsg).
3. Hardening final (checklist `REMEDIACION_SEGURIDAD_SAR.md`): logs PII con structlog cableado, descarga `/media/` segura con policy de pertenencia.
4. **QA E2E**: pendiente #3 onboarding (MFA super-admin y recuperación de contraseña ya ✅). Ver HANDOFF.
5. No bloqueantes: MFA obligatorio para `Usuario`/`CuentaProveedor` del tenant; servicio externo de Mesa de Ayuda (ISSUE-006).

## Nota de precisión (2026-07-02)

Una pasada anterior de esta documentación marcó `dispositivos`, `mensajeria` y `cumplimiento` como
no iniciados/stub sin verificar el código fuente. Se corrigió tras leer `authentication.py`,
`tasks.py` y `services.py` de cada app: los tres tienen backend funcional. Lección: **verificar
código real antes de documentar estado** — no asumir desde nombres de carpetas o memoria de sesión.
