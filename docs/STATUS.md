# Estado del Proyecto — Xenty Acceso

> Actualizado: 2026-07-02

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
| cumplimiento | ⚠ | Backend ✔ (`importar_efos_task` con retry, modelo EFOS); sin pantalla en frontend-acceso |
| ocr | ✔ | Textract + sandbox para INE |
| config | ✔ | Opcion, HistorialCambio, AuditViewSetMixin, DashboardView, CalendarioView, ExportarAccesosView (F8) |
| soporte | ⚠ | SaludConfiguracionView (stub Nivel B) |
| dispositivos | ✔ | `EdgeHMACAuthentication` con nonce anti-replay (Redis); `DispositivoEdge`/`ComandoEdge` en apps.tenants |

## Frontends

| SPA | Estado | Detalle |
|---|---|---|
| frontend-acceso | ✔ | Auth, Dashboard, Usuarios+Permisos, Eventos, Citas, Acceso, Sanciones, Mensajería, Verificación |
| frontend-proveedores | ✔ | Auth, Onboarding, Dashboard, Empleados (foto+docs), MisEventos, Documentos |
| frontend-admin | ⚠ | Layout + lista Tenants; sin CRUD ni billing |

## Infraestructura

| Componente | Estado |
|---|---|
| Docker Compose | ✔ Postgres 15 + Redis 7 + backend + Nginx |
| Celery worker/beat | ✔ Tasks activas: `enviar_campana` (mensajería), `importar_efos_task` (cumplimiento), ambas con retry |
| Nginx dev proxy | ✔ tenant.localhost:8080 |
| CI/CD | 🔲 No configurado |

## Seguridad

| Ítem | Estado |
|---|---|
| Argon2id passwords | ✔ |
| JWT blacklist + rotación | ✔ |
| Fernet QR (jti+exp+tenant) | ✔ |
| PII cifrada (ine_data, curp) | ✔ |
| Rate limiting | ⚠ Configurado en settings, no verificado |
| MFA TOTP | ✔ Enrolamiento + activación + verificación |
| WebAuthn | 🔲 |

## Pendientes críticos

1. Tests pytest — suite de aislamiento entre tenants (existe `tests/test_f0_modelos.py`, 58 líneas; falta la suite `-k aislamiento` obligatoria per CLAUDE.md)
2. Pantalla de cumplimiento SAT 69-B en frontend-acceso (backend ya implementado)
3. Verificar Nginx sirve `/media/` en dev

## Bloqueadores

Ninguno activo.

## Próximos objetivos

1. Tests de aislamiento entre tenants
2. Pantalla frontend de cumplimiento
3. Frontend-admin funcional (CRUD tenants, billing)
4. Auditar cobertura real del ETL F8 (`etl/transformers.py` + `migrar_tenant_sar` ya existen como scaffold, 63 y 64 líneas — falta confirmar si cubren todo `MIGRACION_DATOS_SAR.md`)

## Nota de precisión (2026-07-02)

Una pasada anterior de esta documentación marcó `dispositivos`, `mensajeria` y `cumplimiento` como
no iniciados/stub sin verificar el código fuente. Se corrigió tras leer `authentication.py`,
`tasks.py` y `services.py` de cada app: los tres tienen backend funcional. Lección: **verificar
código real antes de documentar estado** — no asumir desde nombres de carpetas o memoria de sesión.
