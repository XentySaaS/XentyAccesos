# PLAYBOOK_SAR_XENTY — Migración del Sistema de Acceso a Recintos al stack Xenty

> **Documento maestro.** Plan de implementación por fases para reconstruir el SAR
> (hoy Laravel 12 + Filament + MySQL) sobre el stack tecnológico oficial de Xenty
> (Django 5 + DRF + django-tenants + PostgreSQL + React SPA).
>
> Este playbook es la fuente de verdad del proyecto. Ancla al resto de entregables:
> `CLAUDE.md`, `SAR_FUNCIONALIDADES.md`, `MODELO_DATOS_SAR.md`, `MIGRACION_DATOS_SAR.md`,
> `REMEDIACION_SEGURIDAD_SAR.md`, `PROMPT_CLAUDE_DESIGN_SAR.md`.
>
> Producto: **Xenty Acceso** (tercer producto de la suite, junto a XentyFiscal y XentyNominayRH).

---

## 0. Cómo usar este documento

Está escrito para ejecutarse con **Claude Code** bajo un **protocolo de checkpoint por fase**:

1. Claude Code lee este playbook y el `CLAUDE.md` antes de tocar código.
2. Implementa **una fase a la vez**, completa (backend + frontend + tests del slice).
3. Al terminar cada fase: corre los tests, presenta un resumen de lo construido contra los
   **criterios de aceptación**, y **se detiene**. No avanza a la siguiente fase sin revisión y
   aprobación explícita del responsable del proyecto.
4. Nada de la deuda de seguridad del sistema origen se porta. La sección 7 es contractual.

Convención de estados de tarea en cada fase: `[ ]` pendiente · `[~]` en progreso · `[x]` aceptado en checkpoint.

---

## 1. Qué es el SAR y de dónde partimos

Plataforma **SaaS multitenant de control de accesos a recintos** (estadios, museos, plantas
industriales). Dominio central `xenty.mx`; cada cliente opera en su propio subdominio con datos
totalmente aislados. Casos de uso: gestión de **eventos** con proveedores externos, **citas**
puntuales, **verificación documental** (REPSE/SUA/INE), **acceso físico** por gafete QR (panel de
guardias y dispositivos edge Raspberry Pi), **estacionamiento**, **cumplimiento SAT 69-B**,
**sanciones** y **mensajería WhatsApp**.

### Origen (no portar tal cual)

| Capa | Origen | Destino Xenty |
|---|---|---|
| Lenguaje / framework | PHP 8.2 / Laravel 12 | Python 3.12 / Django 5.0.6 + DRF 3.15 |
| UI | Filament 3.3 (3 paneles, render en servidor) + Livewire | **Reconstruida**: React 18 + Vite + shadcn/ui (3 SPAs) |
| Multitenancy | stancl/tenancy — **BD MySQL por tenant** | django-tenants — **schema PostgreSQL por tenant** |
| Roles/permisos | spatie/laravel-permission | DRF + permission classes (`RequiereModulo`, `RequiereMembresia`) |
| Auth dispositivos | HMAC-SHA256 custom | HMAC-SHA256 (reimplementado + nonce anti-replay) |
| Auth usuarios | guards `web` (User) y `provider` (Provider) | **Dos contextos JWT**: `users` y `providers` |
| Cola / cache / sesión | driver `database` (MySQL) | Celery + Redis 7 |
| Cifrado QR/tokens | AES-128-ECB clave fija en git ⚠ | Fernet / tokens firmados (ver §7) |

El aislamiento por base de datos mapea 1:1: BD central → schema `public`; cada BD tenant →
schema por tenant. Identificación por subdominio idéntica. **El grueso del esfuerzo es la UI**,
que no se convierte sino que se reconstruye como API REST + SPAs.

---

## 2. Decisiones arquitectónicas fijadas (contrato)

Estas decisiones están **cerradas**. No se renegocian durante la implementación; cualquier cambio
exige actualizar este playbook primero.

1. **Reconstrucción limpia, no paridad 1:1.** El esquema destino se rehace en Postgres corrigiendo
   los typos (`assistent_appointments` → `asistentes_cita`, `result__lista69bs`,
   `authorized_areas_event_supppliers`, modelo `Change_history`), añadiendo las FKs faltantes
   (`locations.parent_id`, `entries.parent_id`, `assistent_appointments.person_id`) e índices
   (`access_logs` por tiempo, `message_recipients.status`, `change_histories.user_id`). La deuda
   de seguridad se repara de raíz (§7). El comportamiento de negocio se preserva; el esquema y el
   código no.

2. **Implementación vertical por módulo.** Cada fase entrega un slice completo: modelos +
   migraciones + serializers/viewsets DRF + pantallas React + tests. No se hace "todo el backend y
   luego todo el frontend".

3. **Control plane completo desde el arranque.** Tenant/Plan/Suscripción + billing Stripe
   (suscripción + paquetes de créditos + webhooks, con modo sandbox) + MFA (TOTP + WebAuthn) +
   integración con **Mesa de Ayuda** (Nivel B, solo lectura de salud de configuración).

4. **Dos contextos de autenticación en el tenant.** `User` (operación del recinto, contexto
   `acceso`) y `Provider` (autoservicio de empresas externas, contexto `proveedores`) son modelos
   authenticatables **separados**, con flujos JWT distintos. No se colapsan en un `User` con
   discriminador: son audiencias genuinamente distintas y el proveedor nunca accede a la operación.

5. **Tres superficies SPA.** `admin` (control plane / super-admin), `acceso` (operación, auth
   `users`) y `proveedores` (autoservicio, auth `providers`).

6. **Edge por long-polling.** Los dispositivos Raspberry Pi conservan el patrón pull/ack/create
   sobre `edge_commands`. SSE queda reservado para superficies browser→servidor. Se corrige el bug
   `->whilere(...)` y se añade nonce anti-replay al HMAC.

7. **Integraciones detrás de interfaz.** UltraMsg (WhatsApp) y AWS Textract (OCR INE) se conservan
   pero abstraídos en `services/` para ser intercambiables sin tocar el dominio.

8. **Sin agente de IA de dominio al lanzar.** El soporte se cubre vía Mesa de Ayuda. Un agente de
   pago se evaluará después; el control de acceso no tiene un cómputo de dominio que lo justifique hoy.

---

## 3. Stack tecnológico destino (resumen)

Detalle completo y justificaciones en `ARQUITECTURA_Y_STACK_TECNOLOGICO.md`. Resumen operativo:

- **Backend**: Python 3.12 · Django 5.0.6 · DRF 3.15 · djangorestframework-simplejwt 5.3 ·
  django-tenants 3.7 · PostgreSQL 15 · Celery 5.4 · Redis 7 · cryptography (Fernet) ·
  argon2-cffi · pyotp · webauthn · stripe · structlog · sentry-sdk · drf-spectacular ·
  django-filter · django-cors-headers · python-decouple.
- **Frontend (×3 SPA)**: TypeScript 5.5 · React 18.3 · Vite 5.3 · shadcn/ui (Radix) ·
  TailwindCSS 3.4 · Zustand · React Router 6 · Axios (interceptores JWT) · Recharts ·
  lucide-react · qrcode.react. SPA `admin` incluye `@stripe/react-stripe-js`.
- **Específico del dominio SAR** (reemplaza dependencias PHP): generación QR + gafetes
  (`qrcode[pil]`, Pillow) · OCR (`boto3` → Textract) · Excel (`openpyxl`) · PDF protocolos
  (`reportlab`) · WhatsApp (`requests` → UltraMsg) · validación RFC (lib o validador propio).
- **Infra**: Docker Compose (Postgres 15 Alpine, Redis 7, Mailpit dev), Nginx (prod), Node 20.

---

## 4. Arquitectura de planos

```
┌──────────────────────────── CONTROL PLANE (schema public) ─────────────────────────────┐
│  SPA admin (React)            superadmin-backend (Django, settings.control_plane,        │
│                               urls_public.py)                                            │
│  Gestiona: Tenant, Plan, Suscripción, créditos, billing Stripe, dispositivos edge,       │
│            ventanas de mantenimiento, ConfiguracionMesa                                  │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                   │ provisioning (CREATE SCHEMA + migrate_schemas)
                                   ▼
┌──────────────────────────── DATA PLANE (schema por tenant) ────────────────────────────┐
│  SPA acceso  (auth users)     ─┐                                                         │
│  SPA proveedores (auth providers)│→ backend (Django + django-tenants, urls.py)          │
│  rutas públicas (onboarding, QR) ─┘   celery-worker (tenant-aware) · celery-beat         │
│  Dominio: recintos, proveedores, empleados, documentos, eventos, citas, acceso,          │
│           gafetes, dispositivos(tenant), sanciones, mensajería, cumplimiento, ocr        │
└──────────────────────────────────────────────────────────────────────────────────────┘
        │                                   │                            │
   PostgreSQL (public + por tenant)    Redis (broker+cache)      Storage por schema
        │                                                               │
   Stripe · Mesa de Ayuda API · UltraMsg · AWS Textract · SAT 69-B (CSV) · Dispositivos edge (HMAC)
```

**Separación de URLs**: `config/urls.py` (data plane, schema del tenant) ·
`config/urls_public.py` (control plane + webhooks Stripe, schema `public`).

---

## 5. Multitenancy y partición de apps

`SHARED_APPS` (schema `public`):
`django_tenants`, `apps.tenants` (Tenant, Domain, Plan, Suscripcion, SaldoCreditos,
MovimientoCredito, IntentoPago, Factura, SuperAdmin, Version, VentanaMantenimiento,
ConfiguracionMesa, **DispositivoEdge**, **ComandoEdge**), `django.contrib.contenttypes`,
`django.contrib.staticfiles`.

> Nota de diseño: los dispositivos edge y su cola de comandos viven en `public` (igual que hoy
> `devices_tenants` y `edge_commands` están en la BD central), pero cada dispositivo apunta a su
> tenant y la validación cruzada de tenant es obligatoria (§7, C7).

`TENANT_APPS` (schema por tenant):
`django.contrib.auth`, `admin`, `sessions`, `messages`, `rest_framework`, `simplejwt`,
`simplejwt.token_blacklist`, `corsheaders`, `django_filters`, `drf_spectacular`,
`apps.accounts` (User), `apps.proveedores` (Provider+Supplier), `apps.empleados`,
`apps.recintos`, `apps.documentos`, `apps.eventos`, `apps.citas`, `apps.acceso`,
`apps.gafetes`, `apps.sanciones`, `apps.mensajeria`, `apps.cumplimiento`, `apps.ocr`,
`apps.dispositivos` (vistas/lógica tenant de edge), `apps.soporte` (cliente Mesa de Ayuda).

Migraciones: `migrate_schemas --shared` (public) y `migrate_schemas --tenant` (todos los tenants).
Nunca `migrate` solo. Storage por schema vía `TenantFileSystemStorage`.

### Mapa módulo SAR → app Django

| App | Reemplaza (Filament/Laravel) | Modelos núcleo |
|---|---|---|
| `recintos` | Precinct/Zone/Access/Location/Entry/AuthorizedArea Resources | Recinto, Zona, Acceso, Ubicacion, Entrada, AreaAutorizada |
| `proveedores` | SupplierResource + Provider (guard) + onboarding | Proveedor (Supplier), CuentaProveedor (Provider) |
| `empleados` | EmployeeResource | Empleado |
| `documentos` | GroupDocument/ListDocument/EmployeeDocument + checkdocs | GrupoDocumentos, TipoDocumento, DocumentoEmpleado |
| `eventos` | EventResource + EventSupplier + verifiers + parking | Evento, EventoProveedor, CajonParking |
| `citas` | AppointmentResource + AssistantAppointment + Contact | Cita, AsistenteCita, Contacto |
| `acceso` | AccessLogResource + escáneres QR/parking | RegistroAcceso, RegistroAccesoParking |
| `gafetes` | GenerateBadge + QR | (servicio; emite credenciales firmadas) |
| `sanciones` | WarningResource | Sancion |
| `mensajeria` | MessageResource + jobs WhatsApp | Mensaje, DestinatarioMensaje |
| `cumplimiento` | List69b + sat_efos + CheckList69b | SatEfo, ConsultaLista69b, ResultadoLista69b |
| `ocr` | ReadIneOCRController + UtilsController (OCR) | (servicio Textract; `ine_data` cifrado) |
| `dispositivos` | ApiDevicesController + LongPollController (lado tenant) | (vistas HMAC + long-poll; modelos en `public`) |

---

## 6. Modelo de roles y permisos

```
Nivel 1 — SuperAdmin (public): gestiona Tenants, Planes, Suscripciones, créditos, billing.
          No accede a datos operativos de los tenants.
Nivel 2 — User del tenant (contexto acceso): rol operativo + módulos habilitados.
          Roles SAR: Administrator, Editor, Security Guard, Manager, Receptionist, User, Verifier.
Nivel 3 — Provider del tenant (contexto proveedores): rol Admin/User dentro de su Supplier.
          Solo ve sus empleados, documentos, eventos y citas asignados.
```

`RequiereModulo` (permission class DRF) verifica módulo activo del tenant (HTTP 402 si no).
`RequiereRol(*roles)` y `RequiereMembresia` para permisos granulares. **No** hardcodear IDs de rol
como hace hoy `UserResource` (1..6): usar nombres/claves estables.

---

## 7. Requisitos de seguridad transversales (contractual — no portar deuda)

Detalle por hallazgo en `REMEDIACION_SEGURIDAD_SAR.md`. Reglas obligatorias en todo el proyecto:

1. **Sin secretos en el repo.** Todo vía `python-decouple` + `.env` (no versionado). `.env.example`
   documenta cada variable. Rotar todas las credenciales heredadas (BD, SSH/IONOS, AWS, Gmail,
   UltraMsg) antes de cualquier despliegue. No replicar la carpeta `temporal/`.
2. **QR de acceso físico inviolable** (reemplaza C3 AES-128-ECB clave `'Elevation2025'`): payload
   firmado con HMAC-SHA256 o cifrado con Fernet (clave `SECRET_KEY_FERNET` separada de
   `SECRET_KEY`), con identificador único por emisión y vigencia embebida. Los QR del sistema viejo
   se invalidan; se reemiten al migrar.
3. **Tokens de invitación de proveedor firmados** (reemplaza `GenerateUrlContract`): token firmado
   con vigencia (72h) verificable sin estado, o registro en BD con expiración. Nunca el esquema
   `sha1(clave.exp)` actual.
4. **Cero rutas operativas sin auth.** `/migrate`, `/clear-cache`, `/syncp`, `/csrf-test`, `/test`
   no existen como endpoints HTTP. Esas operaciones son management commands + CI/CD.
5. **Sin IDOR ni path traversal en archivos.** Todo visor de documentos (REPSE/SUA/INE/empleado)
   exige autenticación + policy de pertenencia + storage privado por schema. Nada de PII en disco
   `public`. Validar/normalizar cualquier parámetro de ruta.
6. **PII de INE cifrada en reposo.** `ine_data` y la imagen INE → campos `encrypted` (Fernet) y
   storage privado. Cumplimiento LFPDPPP.
7. **Aislamiento de dispositivos edge.** HMAC con `hash_equals`/`compare_digest` + ventana de
   tiempo + **nonce/jti anti-replay** (corrige A1). Corregir el filtro por dispositivo (bug
   `whilere`, C6) y verificar pertenencia de empleado/evento al tenant del dispositivo (C7).
8. **Uploads validados.** MIME + extensión + tamaño en todo upload (onboarding proveedor, docs,
   protocolos). Nunca confiar en `getClientOriginalName`.
9. **Rate limiting** en `/api/v1/*` (edge), endpoints públicos de tenant, login y reset de password.
10. **Argon2id** para passwords (ambos contextos). **JWT con blacklist** y rotación de refresh.
    `DEBUG=False` y stack traces ocultos fuera de dev. Sentry con scrubbing de PII (RFC, CURP, email).
11. **Suite de aislamiento entre tenants** obligatoria: un tenant no puede leer datos de otro
    (datos, archivos, cache, comandos edge). La cache tenancy **sí** se aísla (corrige A5).

---

## 8. Protocolo de checkpoint por fase

Al cerrar cada fase, Claude Code entrega y se detiene:

1. **Resumen**: apps/modelos/endpoints/pantallas creados, decisiones tomadas, desviaciones.
2. **Tests verdes**: unitarios + de integración del slice + (desde F1) los de aislamiento de tenant.
3. **DoD**: marca cada criterio de aceptación de la fase como cumplido con evidencia.
4. **Migraciones**: generadas, nunca editadas a mano; `migrate_schemas --shared`/`--tenant` corren limpio.
5. **Revisión**: espera aprobación. Solo entonces avanza. Si hay observaciones, se corrigen dentro
   de la misma fase antes de avanzar.

---

## 9. Fases de implementación (F0–F8)

### F0 — Cimientos, control plane, auth y shells

**Objetivo**: esqueleto ejecutable con multitenancy, control plane completo, dos contextos de auth,
MFA, billing en sandbox, Mesa de Ayuda conectada y las tres SPAs arrancando vacías.

**Entregables**
- [ ] Monorepo: `backend/`, `frontend-acceso/`, `frontend-proveedores/`, `frontend-admin/`.
- [ ] Docker Compose: Postgres 15, Redis 7, Mailpit, backend, celery worker+beat, los 3 frontends.
- [ ] Settings split (`base/dev/prod/control_plane`), decouple, structlog, Sentry, CORS, drf-spectacular.
- [ ] django-tenants: `SHARED_APPS`/`TENANT_APPS` (§5), router, `TenantFileSystemStorage`.
- [ ] `apps.tenants`: Tenant, Domain, Plan, Suscripcion, SaldoCreditos, MovimientoCredito (ledger
      append-only), IntentoPago, Factura, SuperAdmin, Version, VentanaMantenimiento,
      ConfiguracionMesa, DispositivoEdge, ComandoEdge.
- [ ] Provisioning de tenant: `CREATE SCHEMA` + `migrate_schemas --schema` + usuario admin inicial.
- [ ] **Dos contextos JWT**: `apps.accounts` (User, contexto acceso) y `apps.proveedores` (Provider,
      contexto proveedores) con `TenantAwareJWTAuthentication`, blacklist y rotación.
- [ ] MFA: TOTP (pyotp) + WebAuthn (passkeys); `EnforceMFAFullSession`.
- [ ] Billing Stripe: suscripción + paquetes de crédito + webhooks en `urls_public.py`; modo sandbox
      si falta `STRIPE_SECRET_KEY`. Ciclo de vida del tenant (trial→activo→suspendido→cancelado).
- [ ] Stack de middleware en orden (tenant → enforcement → CORS → estándar), con whitelist de rutas.
- [ ] `apps.soporte`: cliente de Mesa de Ayuda (Nivel B, solo lectura de salud de config).
- [ ] Roles/permisos: `RequiereModulo`, `RequiereRol`; siembra de roles SAR por clave estable.
- [ ] Tres shells React (Vite + shadcn + Tailwind + Zustand + Router + Axios con interceptor JWT
      y manejo de 401/refresh). Login + MFA funcionando en `acceso` y `proveedores`; login en `admin`.
- [ ] `argon2-cffi` como hasher; `DEBUG=False` por defecto fuera de dev.

**Criterios de aceptación**
- Crear un tenant desde el control plane provisiona schema + migraciones + admin sin intervención manual.
- Login + MFA completo en ambos contextos del tenant; login en el super-admin.
- Webhook de Stripe en sandbox transiciona el estado del tenant.
- Suite de aislamiento base verde (un tenant no ve datos de `public` ni de otro tenant).

---

### F1 — Recintos + Proveedores + Empleados

**Objetivo**: identidad física y de proveedores, con el onboarding de proveedor end-to-end seguro.

**Entregables**
- [ ] `apps.recintos`: Recinto, Zona, Acceso, Ubicacion (con FK `parent_id` real), Entrada
      (FK `parent_id` real), AreaAutorizada. Endpoints CRUD + filtros.
- [ ] `apps.proveedores`: Proveedor (Supplier: RFC, razón social, email responsable único,
      archivos REPSE/SUA) y CuentaProveedor (Provider). Validación de RFC (estructura + checksum).
- [ ] Onboarding de proveedor: invitación con **token firmado** (vigencia 72h, §7.3), alta de
      datos + archivos con validación MIME/tamaño, transición `pending→confirmed`.
- [ ] `apps.empleados`: Empleado (con foto), import Excel (openpyxl, `firstOrNew` por email).
- [ ] React: pantallas de recintos y proveedores en SPA `acceso`; alta/edición de empleados y
      onboarding en SPA `proveedores`.

**Criterios de aceptación**
- Flujo completo de invitación → alta de proveedor con token firmado verificable y expirable.
- CRUD de recintos/zonas/accesos con la jerarquía correcta y FKs íntegras.
- Import de empleados por Excel idempotente por email.
- Sin acceso a archivos sin auth + policy de pertenencia.

---

### F2 — Documentos y validación documental (`checkdocs`)

**Objetivo**: catálogo de documentos, carga por proveedor, verificación y la regla `checkdocs`.

**Entregables**
- [ ] `apps.documentos`: GrupoDocumentos, TipoDocumento, DocumentoEmpleado
      (`verified`: 0 pendiente / 1 verificado / 2 rechazado), pivote evento↔grupo con
      `type_validation` (0 = al menos uno / 1 = todos).
- [ ] Upload por el proveedor con validación MIME/tamaño (PDF/JPG/PNG ≤2MB) a storage privado por schema.
- [ ] Lógica `checkdocs`: por cada grupo del evento aplica `type_validation`; si todos cumplen →
      `EventoProveedor.empleado.statusdocs = 1`.
- [ ] Flujo de verificación (rol Verifier, filtrado a sus eventos): aprobar/rechazar; rechazo
      notifica al proveedor (email). Alta de documento notifica a verificadores/admins.
- [ ] React: bandeja de verificación (acceso) y carga de documentos (proveedores).

**Criterios de aceptación**
- `checkdocs` respeta `type_validation` 0 y 1 en escenarios mixtos.
- Rechazo de documento dispara notificación al proveedor; alta dispara notificación a verificadores.
- Verifier solo ve documentos de sus eventos asignados.

---

### F3 — Eventos

**Objetivo**: núcleo operativo: eventos, proveedores invitados, grupos de documentos requeridos,
verificadores, estacionamiento y asignación masiva.

**Entregables**
- [ ] `apps.eventos`: Evento (máquina de estados `scheduled→ongoing→completed`, `cancelled` por
      acción; `end_time >= start_time`), EventoProveedor (zona/acceso/protocolo/parking/`limit`),
      pivotes evento↔grupo/documento, verificadores↔evento, CajonParking (uuid en el QR).
- [ ] Reglas: evento no eliminable con proveedores/empleados; cancelar dispara WhatsApp a proveedores;
      usuario no admin solo ve sus eventos.
- [ ] Asignación masiva (lado proveedor): valida `limit`, exige documentos verificados, sincroniza
      pivote con `statusdocs`, dispara emisión de gafete (se completa en F5).
- [ ] Protocolos (PDF ≤10MB) en `apps.recintos` o módulo propio según convenga.
- [ ] React: CRUD de eventos + relación de proveedores (acceso); "mis eventos" + asignación masiva (proveedores).

**Criterios de aceptación**
- Ciclo de vida completo del evento con todas las restricciones de borrado y transición.
- Cancelación notifica por WhatsApp a todos los proveedores del evento.
- Asignación masiva respeta `limit` y exige docs verificados.

---

### F4 — Citas y OCR de INE

**Objetivo**: visitas puntuales (proveedor y directas) y captura/parseo de INE de asistentes.

**Entregables**
- [ ] `apps.citas`: Cita (`type` 0 proveedor / 1 directa; `appointment_type`
      scheduled/walk-in/emergency; cascada Recinto→Zona→Ubicación→Acceso), AsistenteCita
      (`ine_data` **cifrado**, requires_ine, person_id con relación explícita), Contacto reutilizable.
- [ ] `walk-in`: el flujo crea el RegistroAcceso de entrada automáticamente (se cablea con F5).
- [ ] `apps.ocr`: servicio Textract detrás de interfaz; parseo de campos INE con validadores;
      eliminar la validación hueca `validaSeccionINE` (implementar de verdad o quitarla).
      `ine_data` cifrado + imagen en storage privado.
- [ ] No eliminable: cita type=0 con empleados, type=1 con asistentes.
- [ ] React: gestión de citas (acceso); asignación de empleados a cita (proveedores).

**Criterios de aceptación**
- Ambos tipos de cita funcionan con su cascada de selección obligatoria.
- `walk-in` genera registro de acceso automático.
- OCR parsea y **cifra** los datos del INE; ninguna PII en claro ni en disco público.

---

### F5 — Gafetes, QR firmado, acceso físico y sanciones

**Objetivo**: emisión de credenciales inviolables, escaneo y bitácora de acceso, sanciones.

**Entregables**
- [ ] `apps.gafetes`: emisión de QR **firmado/cifrado** (§7.2) con payload `id|contexto|tipo`
      (01 evento / 02 parking / 03 cita) + identificador único + vigencia; gafete PNG con QR (Pillow).
- [ ] `apps.acceso`: RegistroAcceso (`access_type` entry/denied; `access_method` QR/placa/manual/
      tarjeta; índices por tiempo) y RegistroAccesoParking. Validación al escanear: pertenencia,
      vigencia (`start_time ≤ hoy ≤ end_time`), `statusdocs=1`, sanciones activas. Registrar salida.
- [ ] Escáner web (rol Guard) como componente React + endpoint; escáner de parking.
- [ ] `apps.sanciones`: Sancion (`severity` Bajo/Medio/Alto, `penalty` Advertencia/Suspensión/Baja
      solo editables por Admin; Suspensión exige fechas).
- [ ] WhatsApp de confirmación al registrar entrada/salida.
- [ ] React: escáner + bitácora de accesos + sanciones (acceso).

**Criterios de aceptación**
- El QR no es falsificable conociendo el código fuente (firma/cifrado correcto, sin clave estática).
- El escaneo valida pertenencia, vigencia, `statusdocs` y sanciones; registra entrada/salida.
- Sanciones con reglas de severidad/penalidad y fechas correctas.

---

### F6 — Dispositivos edge (HMAC + long-poll)

**Objetivo**: API para dispositivos Raspberry Pi en torniquetes/plumas, con aislamiento correcto.

**Entregables**
- [ ] `/api/v1/*` con middleware HMAC-SHA256 (firma `METHOD-PATH-TIMESTAMP`, `compare_digest`,
      ventana de tiempo, **nonce anti-replay**).
- [ ] Validación de QR de evento/parking/cita desde el dispositivo, **verificando pertenencia al
      tenant del dispositivo** (corrige C7).
- [ ] `edge_commands` (en `public`): long-poll `pull` → `sent`, `ack` → `ack`, `create`
      (`relay.open`, `display.text`). Corregir el filtro por dispositivo (corrige C6 `whilere`).
- [ ] Rate limiting en todo `/api/v1/*`.

**Criterios de aceptación**
- Autenticación HMAC con anti-replay efectivo.
- Un dispositivo no puede hacer `ack` de comandos de otro ni leer datos de otro tenant.
- Long-poll funcional (pull/ack/create) con estados correctos.

---

### F7 — Mensajería WhatsApp y cumplimiento SAT 69-B

**Objetivo**: campañas masivas y validación fiscal de proveedores contra la Lista 69-B.

**Entregables**
- [ ] `apps.mensajeria`: Mensaje (segmentación recinto/zona/evento/all) y DestinatarioMensaje
      (estado pending/sent/failed, `external_id` UltraMsg, `progress`). Envío vía Celery; UltraMsg
      detrás de interfaz; índices en `status`.
- [ ] `apps.cumplimiento`: importador del CSV oficial SAT 69-B (Celery beat configurable,
      default mensual; `--force`), SatEfo (rfc indexado, situación), ConsultaLista69b,
      ResultadoLista69b (`query_data` JSON). Estatus bloqueantes configurables (Definitivo, Presunto).
- [ ] Validación del RFC del proveedor contra EFOS al registrarse y en corridas programadas.
- [ ] React: campañas con progreso (acceso); página Lista 69-B + widget.

**Criterios de aceptación**
- Campaña WhatsApp con progreso por destinatario y reintentos.
- Importación 69-B programada + validación por proveedor con resultado consultable.

---

### F8 — Reportes, dashboard, calendario, ETL y hardening final

**Objetivo**: superficie analítica, migración de datos de los tenants existentes y cierre de seguridad.

**Entregables**
- [ ] Dashboard (KPIs: invitados vs ingresados, eventos actuales), calendario (eventos + citas),
      exportación Excel de bitácora de accesos, historial de cambios (auditoría append-only con
      `model/model_id/user_id/action`, índices, **sin** registrar el diff salvo que se decida).
- [ ] **ETL MySQL→Postgres** (ver `MIGRACION_DATOS_SAR.md`) para `rayados`, `3museos`, `tyasa`,
      `acceso`: mapeo de typos a nombres limarios, reconstrucción de FKs, reemisión de QR firmados,
      re-cifrado de PII. Validación de conteos e integridad por tenant.
- [ ] Hardening final: revisión de los 11 requisitos de §7, suite de aislamiento completa
      (datos + archivos + cache + edge), rate limits, scrubbing Sentry, `.env.example` completo.
- [ ] Cobertura ≥80% en apps críticas (acceso, gafetes, documentos, dispositivos, eventos).

**Criterios de aceptación**
- ETL validado sobre al menos un tenant real con conteos y muestras verificadas.
- Suite de aislamiento entre tenants completa en verde.
- Checklist de §7 cerrado.

---

## 10. Estrategia de testing

- `pytest-django` como suite principal; fixtures sin PII real.
- Tests obligatorios por fase (DoD) + **suite de aislamiento entre tenants** desde F1.
- Mocks para UltraMsg, Textract y SAT (respuestas capturadas; sin llamadas reales en tests).
- Tests de seguridad: QR no forjable, anti-replay edge, IDOR/path traversal en archivos, MIME en uploads.

---

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Subestimar la reconstrucción de UI (3 SPAs, ~25 resources) | Vertical por módulo; cada fase entrega su UI; no diferir el frontend |
| Drift modelo↔esquema del origen (columnas en alters) | `MODELO_DATOS_SAR.md` consolida el esquema real antes de modelar |
| Reemisión de QR al migrar (los viejos quedan inválidos) | Plan de reemisión en F8 + comunicación; ventana de corte por tenant |
| Pérdida de PII INE en el traslado | Re-cifrado en ETL; nunca pasar por disco público |
| Portar inadvertidamente deuda de seguridad | §7 contractual + checklist en cada checkpoint |
| Cola `database` del origen sin reintentos | Celery con reintentos por tarea desde F0 |

---

## 12. Glosario de equivalencias rápidas (Laravel → Xenty)

Filament Resource → DRF ViewSet + pantalla React · Livewire component → componente React + endpoint ·
Eloquent Model → Django Model · Job → tarea Celery · Mailable → plantilla + tarea de email ·
Middleware Laravel → middleware Django/DRF permission · `stancl/tenancy` → `django-tenants` ·
guard `web`/`provider` → contextos JWT `users`/`providers` · `get_option()` → modelo de
configuración key-value o settings · spatie permission → permission class DRF.

---

*Fin del playbook maestro. Siguiente documento recomendado: `MODELO_DATOS_SAR.md` (esquema destino
limpio con el mapeo tabla→modelo), que F0–F8 referencian para los detalles de cada modelo.*
