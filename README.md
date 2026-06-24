# Xenty Acceso

**SaaS multitenant de control de accesos a recintos** (eventos, proveedores, citas, gafetes QR,
dispositivos edge, sanciones, mensajería WhatsApp y cumplimiento SAT 69-B).

Es la **reconstrucción** del SAR —hoy en Laravel 12 + Filament + MySQL— sobre el stack oficial de
Xenty: **Django 5 + DRF + django-tenants + PostgreSQL + React**. Tercer producto de la suite Xenty
(junto a XentyFiscal y XentyNominayRH).

> El sistema viejo es **referencia de solo lectura**: se consulta para entender comportamiento, pero
> **no se porta su código ni su deuda** de seguridad (auditoría origen 3.5/10). Ver `docs/`.

---

## Tabla de contenido
- [Arquitectura](#arquitectura)
- [Stack](#stack)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Puesta en marcha](#puesta-en-marcha)
- [Variables de entorno](#variables-de-entorno)
- [Comandos frecuentes](#comandos-frecuentes)
- [Estado del proyecto (fases)](#estado-del-proyecto-fases)
- [Decisiones de seguridad](#decisiones-de-seguridad)
- [Documentación](#documentación)

---

## Arquitectura

Dos planos sobre una sola base de código Django, separados por **schema de PostgreSQL** (aislamiento
por base de datos, no por disciplina de código):

```
CONTROL PLANE (schema public)            DATA PLANE (schema por tenant)
─ SPA admin / super-admin                ─ SPA acceso  (auth Usuario)
─ Tenant, Plan, Suscripción, billing     ─ SPA proveedores (auth CuentaProveedor)
─ DispositivoEdge / ComandoEdge          ─ recintos, proveedores, empleados, eventos,
─ Ventanas de mantenimiento, Mesa Ayuda    citas, acceso, gafetes, sanciones, mensajería…
  (config/urls_public.py)                  (config/urls.py)
```

- **Multitenancy** con `django-tenants`: cada cliente vive en su propio schema, resuelto por
  subdominio (`<slug>.xenty.mx`). Migraciones siempre con `migrate_schemas --shared` / `--tenant`.
- **Dos contextos de autenticación** en el tenant, con flujos JWT separados (no se colapsan):
  `Usuario` (operación, contexto `acceso`) y `CuentaProveedor` (autoservicio, contexto `proveedores`).
  El `SuperAdmin` del control plane es un tercer autenticatable.
- **Enforcement por middleware** en orden estricto (tenant → IP admin → mantenimiento → estado del
  tenant → trial → solo-lectura → MFA → CORS), con whitelist para que el cliente siempre pueda
  loguearse y pagar.

## Stack

| Capa | Tecnologías |
|---|---|
| **Backend** | Python 3.12 · Django 5.0.6 · DRF 3.15 · djangorestframework-simplejwt · django-tenants 3.7 · PostgreSQL 15 · Celery 5.4 · Redis 7 |
| **Seguridad** | cryptography (Fernet) · argon2-cffi · pyotp + webauthn (MFA) · django-ratelimit |
| **Dominio** | qrcode + Pillow (gafetes) · boto3/Textract (OCR INE) · openpyxl · reportlab · requests (UltraMsg) |
| **Frontend (×3 SPA)** | TypeScript 5.5 · React 18 · Vite 5 · shadcn/ui · TailwindCSS · Zustand · React Router · Axios |
| **Infra** | Docker Compose (Postgres 15, Redis 7, Mailpit) · Nginx (prod) · Node 20 |

## Estructura del repositorio

```
xenty/
├── CLAUDE.md                 # Reglas operativas (fuente de verdad para el desarrollo)
├── README.md
├── bootstrap.bat / .sh       # Generadores del esqueleto (Windows / Mac-Linux)
├── docker-compose.yml
├── .env.example              # Toda variable documentada; el .env real nunca se versiona
├── docs/                     # Suite de documentación (ver abajo)
└── backend/
    ├── config/
    │   ├── settings/{base,dev,prod,control_plane}.py
    │   ├── urls.py           # data plane (tenant)
    │   ├── urls_public.py    # control plane (public) + webhooks
    │   ├── middleware/       # enforcement del ciclo de vida
    │   └── celery.py
    ├── common/               # utilidades transversales (campos cifrados, JWT, auth)
    ├── apps/                 # tenants, accounts, proveedores, empleados, recintos,
    │                         # documentos, eventos, citas, acceso, gafetes, sanciones,
    │                         # dispositivos, mensajeria, cumplimiento, ocr, config, soporte
    ├── etl/                  # ETL MySQL→Postgres (F8)
    ├── tests/
    └── manage.py
```

## Puesta en marcha

### Requisitos
- Docker Desktop (Postgres 15 + Redis 7 + Mailpit corren en contenedores)
- Python 3.12 y Node 20 solo si quieres tooling/SPAs locales (opcional)

### Pasos
```bash
# 1) Generar/actualizar el esqueleto (idempotente). En Windows:
bootstrap.bat
#    En Mac/Linux:  ./bootstrap.sh

# 2) Configurar entorno
cp .env.example .env        # (Windows: copy .env.example .env)
#    Genera las dos claves y pégalas en .env:
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(50)).decode())"   # SECRET_KEY
python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())" # SECRET_KEY_FERNET

# 3) Levantar el stack
docker compose up --build

# 4) Migraciones (SIEMPRE con migrate_schemas, nunca 'migrate' a secas)
docker compose run --rm backend python manage.py migrate_schemas --shared

# 5) Provisionar un tenant (schema + migraciones + admin)
docker compose run --rm backend python manage.py crear_tenant rayados rayados.localhost \
    --admin-email admin@rayados.mx --admin-nombre "Admin"
```

> **Desarrollo local sin Docker para el backend**: se incluye soporte para un venv
> (`bootstrap.bat --local-venv`) útil para el IDE; el runtime real sigue siendo el contenedor 3.12.

## Variables de entorno

Definidas en `.env` (no versionado); `.env.example` documenta todas. Las críticas no tienen default
y la app **falla al arrancar si faltan**:

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave de Django (firma de sesiones/JWT). Sin default. |
| `SECRET_KEY_FERNET` | Clave **separada** para cifrar PII y QR (Fernet). Sin default. |
| `DB_*`, `REDIS_URL` | Conexión a Postgres y Redis. |
| `ADMIN_IP_ALLOWLIST` | IPs permitidas para `/admin/` (vacío = libre en dev). |
| `STRIPE_SECRET_KEY` | Vacío ⇒ billing en modo sandbox. |
| `ULTRAMSG_*`, `AWS_*` | WhatsApp y Textract (vacío = deshabilitado). |

## Comandos frecuentes

```bash
docker compose up -d                                  # levantar stack
python manage.py migrate_schemas --shared             # migrar schema public
python manage.py migrate_schemas --tenant             # migrar todos los tenants
python manage.py crear_tenant <slug> <dominio> ...    # provisionar tenant + admin
pytest                                                # suite completa
pytest -k aislamiento                                 # suite de aislamiento entre tenants
ruff check . && ruff format .                         # calidad Python
celery -A config worker -l info                       # worker Celery (dev)
```

## Estado del proyecto (fases)

Implementación por **fases verticales** (F0→F8) con checkpoint y aprobación entre cada una.

| Fase | Alcance | Estado |
|---|---|---|
| **F0.1** | Modelos del control plane, `Usuario`, cifrado Fernet, provisioning | ✅ |
| **F0.2** | Dos contextos JWT (`Usuario`/`CuentaProveedor`) con binding al tenant, rotación y blacklist | ✅ |
| **F0.3** | Stack de middleware + enforcement del ciclo de vida (mantenimiento, inactivos, trial, solo-lectura, IP admin) | ✅ |
| **F0.4** | MFA TOTP (enrolar/activar/verificar) + enforcement por actor (sesión MFA, email verificado). WebAuthn pendiente | 🟡 |
| **F0.5** | Billing Stripe (suscripción + créditos + webhooks, sandbox) + transiciones de estado del tenant | ✅ |
| **F0.6** | `RequiereModulo`/`RequiereRol`/`RequiereMembresia` + Mesa de Ayuda (`apps.soporte`) + siembra de planes | ✅ |
| **F0.7** | Tres shells React (Vite+TS+Tailwind+Zustand+Axios con JWT/refresh). Requiere `npm install` (Node) para arrancar | 🟡 |
| **F1** | Backend ✅ (Recintos · Proveedores+onboarding · Empleados+import Excel). Pantallas React ⏳ | 🟡 |
| **F2** | Backend ✅ (catálogo documental, upload validado, verificación, regla `checkdocs` como servicio). Pantallas React ⏳ | 🟡 |
| **F3–F8** | Eventos · Citas/OCR · Gafetes/Acceso · Edge · Mensajería/69-B · Reportes/ETL | ⏳ |

## Decisiones de seguridad

La migración de stack es la oportunidad de cortar la deuda del origen de raíz (ver
`docs/REMEDIACION_SEGURIDAD_SAR.md`). Ya aplicadas:

- **Sin secretos en el repo**: `python-decouple` + `.env`; `SECRET_KEY` y `SECRET_KEY_FERNET`
  separadas y sin default (la app no arranca sin ellas).
- **PII y secretos cifrados en reposo** con Fernet (`EncryptedCharField`/`EncryptedJSONField`):
  reemplazan el AES-128-ECB con clave fija en git del origen. Verificado: la columna guarda
  ciphertext, no texto claro.
- **JWT con binding al tenant**: un token emitido para un tenant es rechazado en otro.
- **Baja lógica de personas**: el login exige `activo=True`; nunca se borra físicamente.
- **Enforcement con whitelist**: un tenant suspendido o con trial vencido sigue pudiendo
  autenticarse y pagar.

## Documentación

Toda en `docs/` (más `CLAUDE.md` en la raíz):

| Documento | Contenido |
|---|---|
| `CLAUDE.md` | Reglas operativas, stack bloqueado, convenciones, flujo de checkpoint |
| `PLAYBOOK_SAR_XENTY.md` | Plan maestro por fases F0–F8 |
| `MODELO_DATOS_SAR.md` | Esquema destino limpio (modelos, FKs, índices, enums) |
| `SAR_FUNCIONALIDADES.md` | Catálogo funcional (reglas de negocio, máquinas de estado) |
| `REMEDIACION_SEGURIDAD_SAR.md` | Hallazgos de seguridad del origen → fix en el destino |
| `MIGRACION_DATOS_SAR.md` | ETL MySQL→PostgreSQL por tenant |

---

© Xenty SaaS — Xenty Acceso.
