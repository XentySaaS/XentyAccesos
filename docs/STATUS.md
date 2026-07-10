# Estado del Proyecto — Xenty Acceso

> Actualizado: 2026-07-10 (ver `handoffs/HANDOFF_LATEST.md`)

## Backend

| App | Estado | Detalle |
|---|---|---|
| tenants | ✔ | Tenant, Domain, Plan, TenantMainMiddleware |
| accounts | ✔ | Usuario, PermisoUsuario, roles, JWT acceso |
| proveedores | ✔ | CuentaProveedor, Proveedor, onboarding, JWT proveedores |
| empleados | ✔ | CRUD, import Excel, foto (ImageField), docs |
| recintos | ✔ | Recinto, Zona, Acceso, Ubicacion, Entrada, AreaAutorizada, Protocolo |
| documentos | ✔ | TipoDocumento, DocumentoEmpleado, verificación estados |
| eventos | ✔ | Evento, EventoProveedor, asignación empleados, gafete QR |
| citas | ✔ | Cita, AsistenteCita, Contacto, EmpleadoCita, notificación email |
| acceso | ✔ | RegistroAcceso, scanner QR, bitácora |
| gafetes | ✔ | componer_gafete (Premium Dark), estacionamiento, Fernet QR |
| sanciones | ✔ | Sancion CRUD |
| mensajeria | ✔ | MensajeWhatsApp, DestinatarioMensaje, Celery `enviar_campana` con retry (max_retries=3) |
| cumplimiento | ✔ | Backend (`importar_efos_task` con retry) + padrón EFOS global (`apps.efos`) + pantalla `Cumplimiento.tsx` en frontend-acceso |
| ocr | ✔ | Textract + sandbox para INE |
| config | ✔ | Opcion, HistorialCambio, AuditViewSetMixin, DashboardView, CalendarioView, ExportarAccesosView (F8) |
| soporte | ◑ | Mesa de Ayuda Nivel B: salud de config + cliente (probar/enviar, sandbox) + config por tenant + pantalla `Soporte.tsx`. **Cliente-only**: el servicio externo de Mesa aún no existe → ítem de menú **oculto temporalmente** (KNOWN_ISSUES ISSUE-006) |
| dispositivos | ✔ | `EdgeHMACAuthentication` con nonce anti-replay (Redis); `DispositivoEdge`/`ComandoEdge` en apps.tenants |

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
| CD (deploy) | 🔲 Pendiente: sin destino de producción decidido (ver HANDOFF) |

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

1. Hardening final (checklist `REMEDIACION_SEGURIDAD_SAR.md`): logs PII con structlog cableado, descarga `/media/` segura con policy de pertenencia
2. WebAuthn MFA (TOTP ya funciona) — opcional
3. CI/CD + deploy a producción (Nginx prod, secrets)
4. QA E2E + verificación visual autenticada de frontend-admin (requiere login super-admin en dev)

## Nota de precisión (2026-07-02)

Una pasada anterior de esta documentación marcó `dispositivos`, `mensajeria` y `cumplimiento` como
no iniciados/stub sin verificar el código fuente. Se corrigió tras leer `authentication.py`,
`tasks.py` y `services.py` de cada app: los tres tienen backend funcional. Lección: **verificar
código real antes de documentar estado** — no asumir desde nombres de carpetas o memoria de sesión.
