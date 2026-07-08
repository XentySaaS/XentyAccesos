# CLAUDE.md — Xenty Acceso (reglas operativas para Claude Code)

> Léeme **primero, en cada sesión**. Soy la fuente de verdad operativa del proyecto: stack
> bloqueado, reglas no-negociables, comandos y convenciones. Este `CLAUDE.md` vive en la raíz;
> el resto de la suite está en `docs/`. El **plan** vive en
> `docs/PLAYBOOK_SAR_XENTY.md`; los **modelos** en `docs/MODELO_DATOS_SAR.md`; la **seguridad** en
> `docs/REMEDIACION_SEGURIDAD_SAR.md`; el **ETL** en `docs/MIGRACION_DATOS_SAR.md`; el **funcional** en
> `docs/SAR_FUNCIONALIDADES.md`; el **diseño UI** en `docs/PROMPT_CLAUDE_DESIGN_SAR.md`.

---

## 1. Qué estás construyendo

**Xenty Acceso**: SaaS multitenant de control de accesos a recintos (eventos, proveedores, citas,
gafetes QR, dispositivos edge, sanciones, mensajería, cumplimiento SAT 69-B). Es la **reconstrucción**
de un sistema Laravel 12 + Filament + MySQL sobre el stack oficial de Xenty (Django + DRF +
django-tenants + PostgreSQL + React). Tercer producto de la suite (junto a XentyFiscal y XentyNominayRH).

El repo del sistema viejo es **referencia de solo lectura**. Se consulta para entender comportamiento;
**nunca** se copia su código ni sus patrones (ver §4).

### Estado actual y layout en disco (verificado)
> El proyecto ya **no** está en F0: casi todas las apps y las SPAs están construidas. La fuente de
> verdad viva del avance es [`docs/STATUS.md`](docs/STATUS.md) (léela al empezar sesión); esto es un
> resumen. **Verifica el código real antes de documentar estado** — no asumas desde nombres de
> carpetas ni memoria de sesión (lección registrada en STATUS.md, 2026-07-02).
- **Backend feature-complete en casi todas las apps.** Los 18 modelos bajo `apps/` están poblados
  (p. ej. `tenants` ~320 líneas, `eventos` ~180, `citas` ~150), con migraciones, ViewSets DRF,
  servicios y tareas Celery (`enviar_campana`, `importar_efos_task`, ambas con retry). App nueva
  respecto al árbol original: **`apps/efos`** (padrón EFOS **global**, no por tenant, para 69-B).
- **Librería compartida `backend/common/`** (transversal, no es una app Django): `crypto.py` (Fernet
  PII), `signing.py` (QR firmado), `jwt.py` (`TenantAwareJWTAuthentication`), `mfa.py`/`webauthn.py`
  (+ sus `*_api.py`), `permissions.py` (incl. slots 5 y 9 del middleware como permisos DRF),
  `validators.py`, `fields.py`, `cache.py`, `emails.py`/`email_*`, `health.py`, `observability.py`,
  `exceptions.py`, `auth_api.py`. **Reutiliza de aquí** antes de escribir cripto/auth/validación nueva.
- **4 SPAs construidas** (no 3): `frontend-acceso`, `frontend-proveedores`, `frontend-admin` y
  `frontend-landing` (marketing/onboarding público). Estado por SPA en STATUS.md.
- **Tests activos** en `backend/tests/`: aislamiento entre tenants, ARCO, connector provider, modelos
  F0, router de mensajería, WebAuthn. Config pytest en `backend/pyproject.toml`
  (`DJANGO_SETTINGS_MODULE = config.settings.dev`).
- **ETL descartado**: el SAR original solo tuvo datos de prueba → no hay migración. Este build es la
  implementación final (go-live con tenants nuevos vía onboarding self-service). `backend/etl/` y las
  referencias a "F8 migración" quedan como legado; ignóralas salvo instrucción explícita.
- **El repo git es esta carpeta raíz** (`C:\Users\ADMIN\Documents\ProyectosElevation\XentyAccesos`).
  Aquí viven `CLAUDE.md`, `README.md` y ambos bootstrap. Los `.md` de la suite están en `docs/`
  (ARCHITECTURE, DECISIONS, STATUS, ROADMAP, KNOWN_ISSUES, PLAYBOOK/MODELO/REMEDIACION/SAR_*, etc.).
  Los **handoffs** de sesión viven en `handoffs/` (`HANDOFF_LATEST.md` + `history/`); léelos para
  contexto reciente. `bootstrap.bat` (Windows) / `bootstrap.sh` (Mac/Linux) son idempotentes.

---

## 2. Stack bloqueado (no cambiar versiones sin actualizar este archivo)

**Backend**: Python 3.12 · Django 5.0.6 · DRF 3.15.1 · djangorestframework-simplejwt 5.3.1 ·
django-tenants 3.7.0 · PostgreSQL 15 · Celery 5.4.0 · Redis 7 · cryptography (Fernet) ·
argon2-cffi 23.1.0 · pyotp 2.9.0 · webauthn 2.5.0 · stripe 11.1.1 · structlog 24.4.0 ·
sentry-sdk 2.13.0 · drf-spectacular 0.27.2 · django-filter 24.2 · django-cors-headers 4.3.1 ·
django-ratelimit 4.1.0 · python-decouple 3.8.

**Dominio SAR**: qrcode[pil] 7.4.2 + Pillow (gafetes) · boto3 (Textract OCR) · openpyxl 3.1.5 (Excel) ·
reportlab 4.2.2 (PDF protocolos) · requests 2.32.3 (UltraMsg WhatsApp) · validador RFC.

**Frontend (×4 SPA)**: TypeScript 5.5 · React 18.3 · Vite 5.3 · shadcn/ui (Radix) · TailwindCSS 3.4 ·
Zustand 4.5 · React Router 6.24 · Axios 1.7 · Recharts 2.12 · lucide-react · qrcode.react 4.2.
SPA `admin` añade `@stripe/react-stripe-js`; SPA `acceso` añade `html5-qrcode` + `@simplewebauthn/browser`.

**Infra**: Docker Compose (Postgres 15 Alpine, Redis 7, Mailpit) · Nginx (prod) · Node 20.

---

## 3. Estructura del monorepo

```
xenty-acceso/
├── backend/
│   ├── config/
│   │   ├── settings/{base,dev,prod,control_plane}.py
│   │   ├── urls.py            # data plane (schema del tenant)
│   │   ├── urls_public.py     # control plane (schema public) + webhooks Stripe
│   │   ├── celery.py
│   │   └── middleware/        # enforcement.py + idempotency.py (orden en §6)
│   ├── common/                # librería compartida: crypto, signing, jwt, mfa, webauthn,
│   │                          #   permissions, validators, fields, cache, emails, health…
│   ├── apps/
│   │   ├── tenants/           # public: Tenant, Plan, billing, MFA, DispositivoEdge, ComandoEdge…
│   │   ├── accounts/          # tenant: Usuario (contexto acceso), PermisoUsuario, roles
│   │   ├── proveedores/ empleados/ recintos/ documentos/ eventos/ citas/
│   │   ├── acceso/ gafetes/ sanciones/ dispositivos/ mensajeria/ cumplimiento/ ocr/
│   │   ├── efos/              # padrón EFOS GLOBAL (SAT 69-B) — no por tenant
│   │   ├── config/            # Opcion, HistorialCambio, dashboards/export
│   │   └── soporte/           # cliente Mesa de Ayuda (Nivel B)
│   ├── etl/                   # legado (ETL descartado — ver §1)
│   ├── tests/                 # aislamiento, ARCO, connector, WebAuthn, mensajería…
│   ├── conftest.py · pyproject.toml   # config pytest (settings.dev)
│   └── manage.py
├── frontend-acceso/          # SPA operación (auth users) — + scanner QR, WebAuthn
├── frontend-proveedores/     # SPA autoservicio (auth providers)
├── frontend-admin/           # SPA super-admin (control plane) — + Stripe
├── frontend-landing/         # SPA marketing / onboarding público
├── handoffs/                 # HANDOFF_LATEST.md + history/ — contexto de sesiones previas
├── design/ · nginx/ · docker-compose.yml
├── .env.example              # COMPLETO y verificado; nunca .env real en git
└── docs/                     # suite de documentación (STATUS.md = estado vivo)
```

---

## 4. Reglas NO-NEGOCIABLES

### Multitenancy
- **Aislamiento por DB, no por disciplina de código.** Todo dato de tenant vive en su schema.
- Toda tarea Celery que toque modelos `TENANT_APPS` va envuelta en `tenant_context(tenant)`. Sin excepción.
- Migraciones: **siempre** `migrate_schemas --shared` / `--tenant`. **Nunca** `migrate` a secas.
- Cache, storage y comandos edge **aislados por tenant** (cache con prefijo por schema; storage
  privado por schema). Suite de aislamiento obligatoria desde F1.
- `SHARED_APPS`/`TENANT_APPS` se ajustan en su lista fuente; no editar `INSTALLED_APPS` a mano.

### Dos contextos de autenticación
- `Usuario` (contexto `acceso`) y `CuentaProveedor` (contexto `proveedores`) son authenticatables
  **separados**, con flujos JWT distintos. No los colapses en un solo modelo.
- JWT con blacklist + rotación de refresh; `TenantAwareJWTAuthentication` valida pertenencia al tenant.
- Passwords con Argon2id. MFA (TOTP + WebAuthn) en el control plane y disponible en el tenant.

### Seguridad (resumen contractual — detalle en `REMEDIACION_SEGURIDAD_SAR.md`)
- **Sin secretos en el repo.** Todo por `python-decouple` + entorno. `SECRET_KEY` y
  `SECRET_KEY_FERNET` separadas, sin default.
- **QR de acceso firmado/cifrado** (Fernet o HMAC con `jti`+`exp`). **Jamás** AES-ECB ni clave en código.
- **PII cifrada** (Fernet): `ine_data`, `curp`, `nss`, `identification_number`. Imágenes INE y docs en
  **disco privado por schema**. Nunca en `/media` público.
- **Cero endpoints de mantenimiento** (`/migrate`, `/syncp`, `/clear-cache`, etc.). Eso es CLI/CD.
- **Auth + policy de pertenencia** en toda descarga de archivo. Sin parámetros de ruta crudos.
- **Validar uploads** (extensión + MIME real + tamaño). Nombre de archivo lo pone el servidor.
- **Rate limiting** (Redis) en login, reset, onboarding público y `/api/v1/*`.
- **Edge**: HMAC con `compare_digest` + ventana + **nonce anti-replay**; verificación cruzada de tenant.
- **Sin PII en logs** (structlog con redacción; Sentry con scrubbing). `DEBUG=False` fuera de dev.

### Datos y modelos
- Sigue `MODELO_DATOS_SAR.md` al pie: nombres limpios (sin typos del origen), FKs reales, enums como
  `TextChoices`/`IntegerChoices`, índices indicados.
- **Baja lógica de personas**: `Empleado`/`Usuario` se dan de baja (`activo=False` + `fecha_baja`),
  nunca se borran físicamente.
- Migraciones aplicadas no se editan: se generan nuevas.

### No portar deuda
- No copies código, nombres con typo, validaciones huecas (`validaSeccionINE` siempre true),
  controladores god-object ni middleware esqueleto del origen. Si dudas si algo es deuda, lo es:
  consulta `TECHNICAL_DEBT.md`/`SECURITY.md` del repo viejo y reimplementa limpio.

### Evenhandedness operativa
- No inventes alcance fuera de la fase actual. No "mejores" el dominio sin instrucción (p. ej. no
  añadas un agente de IA: está fuera de alcance al lanzar).

---

## 5. Flujo de trabajo (protocolo de checkpoint)

1. Implementa **una fase a la vez** (F0→F8), slice vertical completo: modelos + migraciones + DRF +
   React + tests del módulo.
2. Al cerrar la fase: corre tests (incluida la suite de aislamiento), marca el **DoD** de la fase
   contra evidencia, presenta un resumen y **detente**. No avances sin aprobación explícita.
3. Si hay observaciones, corrige dentro de la misma fase antes de avanzar.
4. Cada fase debe cerrar su deuda de seguridad según la matriz hallazgo→fase de `REMEDIACION_*`.

**Definition of Done genérica por fase**: migraciones limpias (`--shared`/`--tenant`), tests verdes,
aislamiento verde, endpoints documentados (drf-spectacular), UI del slice funcional, ítems de
seguridad de la fase cerrados, `.env.example` actualizado si hubo variables nuevas.

---

## 6. Orden del middleware (crítico)

```
1. TenantMainMiddleware          # resuelve tenant por subdominio (PRIMERO)
2. RestringirAdminPorIP          # /admin/ por allowlist
3. EnforceMantenimiento          # 503 en ventana de mantenimiento
4. BloquearTenantsInactivos      # tenant suspendido/cancelado
5. BloquearEmailNoVerificado
6. BloquearTrialExpirado
7. EnforceModoSoloLectura        # 423 en dunning/retención
8. (cuotas del plan según aplique)
9. EnforceMFAFullSession         # 403 si sesión MFA incompleta
10. CorsMiddleware
11..  estándar Django
```
Cada enforcement tiene whitelist (health, auth, billing, logout) para que el cliente siempre pueda pagar.

> **Cómo está implementado (verificado en `config/settings/base.py`):** los slots **5**
> (email no verificado) y **9** (sesión MFA incompleta) **no** son middleware — se aplican como
> permisos DRF en `common/permissions.py` (`EmailVerificado`, `MFASesionCompleta`), porque requieren
> el actor JWT ya resuelto. El middleware real es solo `enforcement.py` (RestringirAdminPorIP,
> EnforceMantenimiento, BloquearTenantsInactivos, BloquearTrialExpirado, EnforceModoSoloLectura) +
> `idempotency.Idempotency`. El orden numerado de arriba es el **modelo conceptual**; sigue el listado
> `MIDDLEWARE` de `base.py` como fuente de verdad al tocar el pipeline.

---

## 7. Comandos

```bash
# Levantar stack dev
docker compose up -d

# Migraciones (SIEMPRE así)
python manage.py migrate_schemas --shared
python manage.py migrate_schemas --tenant

# Crear/migrar un tenant
python manage.py create_tenant <slug> <dominio>        # provisioning
python manage.py migrate_schemas --schema=<slug>

# Tests (se corren desde backend/; los tests viven en backend/tests/)
pytest                              # toda la suite
pytest tests/test_webauthn.py -q    # un archivo
pytest -k aislamiento               # suite de aislamiento entre tenants (~2.5 min: crea schemas)
# La imagen backend solo trae requirements.txt (prod). Para correr tests en el contenedor:
#   docker compose exec backend pip install -r requirements-dev.txt
#   docker compose exec backend python -m pytest -k aislamiento

# Calidad
ruff check . && ruff format .       # Python
# frontend (en cada SPA)
npm run lint && npm run build

# Celery (dev)
celery -A config worker -l info
celery -A config beat -l info       # PersistentScheduler

# ETL (F8)
python manage.py migrar_tenant_sar <subdominio> --dry-run
```

> Tras cambiar variables de entorno, los workers Celery requieren `--force-recreate`
> (las vars se cargan al crear el contenedor, no al restart).

---

## 8. Convenciones de código

| Ámbito | Convención |
|---|---|
| Python | PEP8; type hints en servicios y modelos; docstrings Google; `ruff` |
| TypeScript | ESLint + Prettier; sin `any`; componentes funcionales con hooks |
| Naming Python | `snake_case` funciones/vars; `PascalCase` clases/modelos; modelos y verbose en **español** |
| Naming TS | `camelCase`; `PascalCase` componentes/tipos |
| API | REST/DRF; rutas en plural; filtros con django-filter; esquema OpenAPI con drf-spectacular |
| Commits | Convencionales: `feat:`, `fix:`, `test:`, `docs:`, `refactor:` |
| Comentarios | Solo el **por qué** no obvio; nunca el qué |
| Estados/enums | `TextChoices`/`IntegerChoices` con etiqueta para UI; nunca enums crudos ni IDs hardcodeados |
| Ayuda contextual | **Todo campo de captura** de un formulario lleva el ícono ⓘ (`<Ayuda>`) junto a su etiqueta, explicando qué es / para qué sirve. Componente: `frontend-acceso/src/components/Ayuda.tsx`; hermano del `Label` (no dentro). Detalle y checklist: [`docs/AYUDA_CONTEXTUAL.md`](docs/AYUDA_CONTEXTUAL.md). NO negociable en formularios nuevos y existentes. |
| Idempotencia | Contra doble-submit (doble clic → registro duplicado): el cliente axios (`src/api/client.ts` de cada SPA) deduplica POST/PUT/PATCH idénticos en vuelo y manda `Idempotency-Key`; el middleware `config.middleware.idempotency.Idempotency` repite la respuesta cacheada (por tenant) en reintentos. **Automático** — no requiere código por formulario. No lo desactives ni mandes peticiones mutadoras fuera del cliente `api`. |

---

## 9. Modelos de IA (solo soporte vía Mesa de Ayuda)

No hay agente de dominio en este producto al lanzar. El cliente de soporte (`apps.soporte`, Nivel B)
solo **lee salud de configuración** para diagnóstico: nunca ejecuta cómputo de dominio ni consume
créditos. Cualquier ampliación se decide fuera de las fases actuales.

---

## 10. Antes de escribir cualquier código, verifica

- [ ] ¿Estoy en la fase correcta del playbook y solo en su alcance?
- [ ] ¿El modelo coincide con `MODELO_DATOS_SAR.md` (nombre limpio, FKs, enums, índices)?
- [ ] ¿Toca PII? → cifrar + disco privado.
- [ ] ¿Toca archivos? → auth + policy de pertenencia, sin ruta cruda.
- [ ] ¿Tarea Celery con modelos de tenant? → `tenant_context`.
- [ ] ¿Estoy a punto de copiar algo del repo viejo? → reimplementar limpio.
- [ ] ¿Migración nueva? → `migrate_schemas`, no `migrate`.
- [ ] ¿Cierro deuda de seguridad de esta fase (matriz de `REMEDIACION_*`)?
