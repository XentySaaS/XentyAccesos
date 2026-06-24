#!/usr/bin/env bash
#
# bootstrap.sh — Esqueleto del monorepo "Xenty Acceso" (SAR sobre el stack Xenty)
#
# Monta la estructura de F0 del PLAYBOOK_SAR_XENTY.md: backend Django + django-tenants
# (split de settings, apps bajo apps/ registradas en SHARED_APPS/TENANT_APPS), 3 SPAs React,
# docker-compose (Postgres 15 / Redis 7 / Mailpit), .env.example completo y .gitignore.
#
# NO implementa modelos ni lógica de negocio: eso es trabajo de Claude Code en F0+.
# El esqueleto deja TODOs claros donde F0 debe completar (modelo Tenant, AUTH_USER_MODEL, etc.).
#
# Las dependencias se instalan dentro del contenedor (docker compose up --build); el script NO
# requiere un Python concreto en tu máquina. El runtime queda fijado por el Dockerfile (python:3.12).
#
# Uso:
#   ./bootstrap.sh                 # monta estructura + archivos (deps van en el contenedor)
#   ./bootstrap.sh --local-venv    # ADEMÁS crea backend/.venv local (conveniencia para IDE; opcional)
#   ./bootstrap.sh --no-frontend   # omite las 3 SPAs
#   PROJECT_DIR=mi-carpeta ./bootstrap.sh
#
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_DIR="${PROJECT_DIR:-xenty-acceso}"
# Python solo para el venv LOCAL opcional. El runtime real es el del contenedor (Dockerfile).
# Autodetecta: prefiere 3.12 (= runtime), si no usa python3/python disponible.
if [ -n "${PYTHON_BIN:-}" ]; then :;
elif command -v python3.12 >/dev/null 2>&1; then PYTHON_BIN=python3.12;
elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3;
else PYTHON_BIN=python; fi
DO_LOCAL_VENV=0           # por defecto NO: las deps viven en el contenedor
DO_FRONTEND=1

for arg in "$@"; do
  case "$arg" in
    --local-venv) DO_LOCAL_VENV=1 ;;
    --no-frontend) DO_FRONTEND=0 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Argumento no reconocido: $arg" >&2; exit 1 ;;
  esac
done

# Versiones del stack (CLAUDE.md §2)
DJANGO_VER="5.0.6"
DRF_VER="3.15.1"

c_info()  { printf '\033[1;34m▸ %s\033[0m\n' "$*"; }
c_ok()    { printf '\033[1;32m✔ %s\033[0m\n' "$*"; }
c_warn()  { printf '\033[1;33m! %s\033[0m\n' "$*"; }

# ─────────────────────────────────────────────────────────────────────────────
# Preflight
# ─────────────────────────────────────────────────────────────────────────────
c_info "Verificando herramientas"
command -v docker >/dev/null 2>&1 || c_warn "Docker no encontrado: lo necesitarás para correr el stack (docker compose up --build)."
if [ "$DO_LOCAL_VENV" = 1 ]; then
  command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Falta '$PYTHON_BIN' para --local-venv. Define PYTHON_BIN o quita el flag." >&2; exit 1; }
fi
HAVE_NODE=1; command -v node >/dev/null 2>&1 || HAVE_NODE=0
HAVE_GIT=1;  command -v git  >/dev/null 2>&1 || HAVE_GIT=0
[ "$DO_FRONTEND" = 1 ] && [ "$HAVE_NODE" = 0 ] && c_warn "Node no encontrado: se omitirán las SPAs (puedes correrlas luego)."

if [ -e "$PROJECT_DIR" ]; then
  echo "El directorio '$PROJECT_DIR' ya existe. Borra o renombra antes de continuar." >&2
  exit 1
fi

c_info "Creando '$PROJECT_DIR'"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
[ "$HAVE_GIT" = 1 ] && git init -q

# ─────────────────────────────────────────────────────────────────────────────
# Árbol base
# ─────────────────────────────────────────────────────────────────────────────
c_info "Creando árbol de directorios"
mkdir -p backend/config/settings backend/config/middleware backend/apps backend/etl backend/tests docs

# Apps de negocio (MODELO_DATOS_SAR.md §4). 'tenants' es SHARED; el resto TENANT.
APPS=(tenants accounts proveedores empleados recintos documentos eventos citas \
      acceso gafetes sanciones dispositivos mensajeria cumplimiento ocr config soporte)

for app in "${APPS[@]}"; do
  mkdir -p "backend/apps/$app/migrations"
  touch "backend/apps/$app/__init__.py" "backend/apps/$app/migrations/__init__.py"
  # Capitaliza la primera letra de forma portable (bash 3.2 de macOS no soporta ${app^})
  app_cap="$(printf '%s' "$app" | cut -c1 | tr '[:lower:]' '[:upper:]')$(printf '%s' "$app" | cut -c2-)"
  # AppConfig con el label "apps.<app>"
  cat > "backend/apps/$app/apps.py" <<PY
from django.apps import AppConfig


class ${app_cap}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.$app"
PY
  # Stubs vacíos (F0+ los llena)
  printf '# Modelos de la app "%s" — implementar según MODELO_DATOS_SAR.md\n' "$app" > "backend/apps/$app/models.py"
  : > "backend/apps/$app/views.py"
  : > "backend/apps/$app/serializers.py"
  : > "backend/apps/$app/admin.py"
done
touch backend/apps/__init__.py
c_ok "Apps creadas: ${APPS[*]}"

# ─────────────────────────────────────────────────────────────────────────────
# manage.py + config (sin depender de django-admin)
# ─────────────────────────────────────────────────────────────────────────────
c_info "Generando config/ y manage.py"

cat > backend/manage.py <<'PY'
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Activaste el venv e instalaste las dependencias?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
PY
chmod +x backend/manage.py

cat > backend/config/__init__.py <<'PY'
from .celery import app as celery_app

__all__ = ("celery_app",)
PY

cat > backend/config/celery.py <<'PY'
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("xenty_acceso")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# NOTA (F0): toda tarea que toque modelos TENANT_APPS debe envolverse en
# tenant_context(tenant). Ver CLAUDE.md §4 (Multitenancy).
PY

cat > backend/config/asgi.py <<'PY'
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_asgi_application()
PY

cat > backend/config/wsgi.py <<'PY'
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()
PY

# ── settings/base.py ─────────────────────────────────────────────────────────
cat > backend/config/settings/base.py <<'PY'
"""
Configuración compartida. Toda la lógica vive aquí; dev/prod/control_plane solo ajustan.
Secretos vía python-decouple (.env). NUNCA hardcodear credenciales (REMEDIACION §C1).
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Seguridad base ───────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY")                 # sin default: falla si falta
SECRET_KEY_FERNET = config("SECRET_KEY_FERNET")   # separada (cifra PII/QR). REMEDIACION §C3
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ── Multitenancy (django-tenants) ────────────────────────────────────────────
SHARED_APPS = [
    "django_tenants",
    "apps.tenants",                  # F0: Tenant, Domain, Plan, billing, DispositivoEdge…
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
]

TENANT_APPS = [
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Apps de negocio (data plane)
    "apps.accounts",
    "apps.proveedores",
    "apps.empleados",
    "apps.recintos",
    "apps.documentos",
    "apps.eventos",
    "apps.citas",
    "apps.acceso",
    "apps.gafetes",
    "apps.sanciones",
    "apps.dispositivos",
    "apps.mensajeria",
    "apps.cumplimiento",
    "apps.ocr",
    "apps.config",
    "apps.soporte",
]

INSTALLED_APPS = list(SHARED_APPS) + [a for a in TENANT_APPS if a not in SHARED_APPS]

# F0: crear estos modelos en apps.tenants y descomentar.
TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": config("DB_NAME", default="xenty_acceso"),
        "USER": config("DB_USER", default="xenty"),
        "PASSWORD": config("DB_PASSWORD", default="xenty"),
        "HOST": config("DB_HOST", default="postgres"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# ── Middleware (orden crítico — CLAUDE.md §6) ────────────────────────────────
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    # F0: enforcement (RestringirAdminPorIP, EnforceMantenimiento, BloquearTenantsInactivos,
    #     BloquearEmailNoVerificado, BloquearTrialExpirado, EnforceModoSoloLectura,
    #     EnforceMFAFullSession) van aquí, antes de CORS.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
PUBLIC_SCHEMA_URLCONF = "config.urls_public"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# ── Auth ─────────────────────────────────────────────────────────────────────
# F0: crear apps.accounts.Usuario y descomentar. El proveedor (apps.proveedores.CuentaProveedor)
# es un SEGUNDO authenticatable con su propio flujo JWT (CLAUDE.md §4), no es AUTH_USER_MODEL.
# AUTH_USER_MODEL = "accounts.Usuario"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# ── DRF + JWT ────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # F0: TenantAwareJWTAuthentication (valida pertenencia al tenant)
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Xenty Acceso API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ── Celery + Redis ───────────────────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", default="redis://redis:6379")
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/1"
CELERY_TASK_DEFAULT_RETRY_DELAY = 30
CELERY_BEAT_SCHEDULER = "celery.beat.PersistentScheduler"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/2",
        # F0: aislar por tenant con KEY_PREFIX por schema (REMEDIACION §A5)
    }
}
RATELIMIT_USE_CACHE = "default"

# ── Storage por tenant (privado) ─────────────────────────────────────────────
STORAGES = {
    "default": {"BACKEND": "django_tenants.files.storage.TenantFileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MULTITENANT_RELATIVE_MEDIA_ROOT = "%s"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5174,http://localhost:5175,http://localhost:5176",
    cast=Csv(),
)

# ── i18n / tz ────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Integraciones (claves vía .env; nunca hardcodear — REMEDIACION §C2) ──────
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")          # vacío → modo sandbox
ULTRAMSG_TOKEN = config("ULTRAMSG_TOKEN", default="")
ULTRAMSG_INSTANCE_ID = config("ULTRAMSG_INSTANCE_ID", default="")
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION = config("AWS_REGION", default="us-east-1")
SAT_EFOS_UPDATE_EVERY_MONTHS = config("SAT_EFOS_UPDATE_EVERY_MONTHS", default=1, cast=int)
SENTRY_DSN = config("SENTRY_DSN", default="")
PY

# ── settings/dev.py ──────────────────────────────────────────────────────────
cat > backend/config/settings/dev.py <<'PY'
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="mailpit")  # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)  # noqa: F405
EMAIL_USE_TLS = False
PY

# ── settings/prod.py ─────────────────────────────────────────────────────────
cat > backend/config/settings/prod.py <<'PY'
from .base import *  # noqa: F401,F403

DEBUG = False
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# F0: Sentry con scrubbing de PII (REMEDIACION §A7) si SENTRY_DSN está presente.
PY

# ── settings/control_plane.py ────────────────────────────────────────────────
cat > backend/config/settings/control_plane.py <<'PY'
"""Para el contenedor superadmin-backend: monta el URLconf público (schema 'public')."""
from .prod import *  # noqa: F401,F403

ROOT_URLCONF = "config.urls_public"
PY

# ── urls.py / urls_public.py ─────────────────────────────────────────────────
cat > backend/config/urls.py <<'PY'
"""Data plane — schema del tenant (por subdominio). F1+ monta las apps de negocio."""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("api/", include("apps.<app>.urls")),  # F1+
]
PY

cat > backend/config/urls_public.py <<'PY'
"""Control plane — schema 'public'. F0 monta gestión de tenants, billing y webhooks Stripe."""
from django.urls import path

urlpatterns = [
    # path("api/tenants/", include("apps.tenants.urls")),       # F0
    # path("webhooks/stripe/", stripe_webhook_view),            # F0
]
PY

touch backend/config/middleware/__init__.py
touch backend/tests/__init__.py
printf '# ETL MySQL→Postgres por tenant (F8). Ver MIGRACION_DATOS_SAR.md\n' > backend/etl/__init__.py

# ─────────────────────────────────────────────────────────────────────────────
# Dependencias del backend
# ─────────────────────────────────────────────────────────────────────────────
c_info "Escribiendo requirements y pyproject"
cat > backend/requirements.txt <<REQ
Django==${DJANGO_VER}
djangorestframework==${DRF_VER}
djangorestframework-simplejwt==5.3.1
django-tenants==3.7.0
psycopg2-binary>=2.9
celery==5.4.0
redis>=5.0
cryptography>=43
argon2-cffi==23.1.0
pyotp==2.9.0
webauthn==2.5.0
stripe==11.1.1
structlog==24.4.0
sentry-sdk==2.13.0
drf-spectacular==0.27.2
django-filter==24.2
django-cors-headers==4.3.1
django-ratelimit==4.1.0
python-decouple==3.8
# Dominio SAR
qrcode[pil]==7.4.2
Pillow>=10
boto3>=1.34
openpyxl==3.1.5
reportlab==4.2.2
requests==2.32.3
python-magic>=0.4.27
REQ

cat > backend/pyproject.toml <<'TOML'
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.dev"
python_files = ["test_*.py", "*_test.py"]
TOML

cat > backend/Dockerfile <<'DOCKER'
# Runtime fijado a 3.12 (matriz de soporte de Django 5.0.6). Independiente del Python local.
# Para subir a 3.13/3.14 hay que cambiar también la versión de Django (decisión de stack).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libmagic1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
DOCKER

# ─────────────────────────────────────────────────────────────────────────────
# docker-compose + .env.example + .gitignore
# ─────────────────────────────────────────────────────────────────────────────
c_info "Generando docker-compose, .env.example y .gitignore"
cat > docker-compose.yml <<'YML'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${DB_NAME:-xenty_acceso}
      POSTGRES_USER: ${DB_USER:-xenty}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-xenty}
    ports: ["5434:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6381:6379"]

  mailpit:
    image: axllent/mailpit:latest
    ports: ["8025:8025", "1025:1025"]

  backend:
    build: ./backend
    command: python manage.py runserver 0.0.0.0:8000
    env_file: [.env]
    volumes: ["./backend:/app"]
    ports: ["8002:8000"]
    depends_on: [postgres, redis]

  celery-worker:
    build: ./backend
    command: celery -A config worker -l info
    env_file: [.env]
    volumes: ["./backend:/app"]
    depends_on: [backend, redis]

  celery-beat:
    build: ./backend
    command: celery -A config beat -l info
    env_file: [.env]
    volumes: ["./backend:/app"]
    depends_on: [backend, redis]

  superadmin-backend:
    build: ./backend
    command: python manage.py runserver 0.0.0.0:8000
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.control_plane
    env_file: [.env]
    volumes: ["./backend:/app"]
    ports: ["8003:8000"]
    depends_on: [postgres, redis]

volumes:
  pgdata:
YML

cat > .env.example <<'ENV'
# ── Núcleo (sin default: la app falla si faltan) ─────────────────────────────
SECRET_KEY=cambia-esto-en-cada-entorno
SECRET_KEY_FERNET=genera-una-clave-fernet-distinta-de-SECRET_KEY
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ── Base de datos ────────────────────────────────────────────────────────────
DB_NAME=xenty_acceso
DB_USER=xenty
DB_PASSWORD=xenty
DB_HOST=postgres
DB_PORT=5432

# ── Redis / Celery ───────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379

# ── CORS (las 3 SPAs) ────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:5174,http://localhost:5175,http://localhost:5176

# ── Email (dev: Mailpit) ─────────────────────────────────────────────────────
EMAIL_HOST=mailpit
EMAIL_PORT=1025

# ── Integraciones (vacío = deshabilitado / sandbox) ──────────────────────────
STRIPE_SECRET_KEY=
ANTHROPIC_API_KEY=
ULTRAMSG_TOKEN=
ULTRAMSG_INSTANCE_ID=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
SAT_EFOS_UPDATE_EVERY_MONTHS=1
SENTRY_DSN=

# NUNCA subas el .env real al repo. Este .env.example se mantiene completo (DoD F0/F8).
ENV

cat > .gitignore <<'GIT'
# Secretos (REMEDIACION §C1) — jamás versionar
.env
*.env
!.env.example

# Python
.venv/
__pycache__/
*.py[cod]
staticfiles/

# Media de tenants (PII) — fuera del repo
media/

# Node
node_modules/
dist/

# Código del stack anterior (mantener como repo hermano, NO aquí)
_ref-sar-legacy/

# OS / editor
.DS_Store
.idea/
.vscode/
GIT

cat > README.md <<'MD'
# Xenty Acceso

Reconstrucción del SAR (control de accesos) sobre el stack Xenty.
Esqueleto generado por `bootstrap.sh` (fase F0 del PLAYBOOK_SAR_XENTY.md).

## Documentación (en `docs/`)
PLAYBOOK_SAR_XENTY · CLAUDE · MODELO_DATOS_SAR · SAR_FUNCIONALIDADES ·
REMEDIACION_SEGURIDAD_SAR · MIGRACION_DATOS_SAR · PROMPT_CLAUDE_DESIGN_SAR

## Arranque rápido
1. `cp .env.example .env` y genera SECRET_KEY y SECRET_KEY_FERNET (ver salida de bootstrap.sh).
2. `docker compose up --build`  (deps en la imagen, Python 3.12 — independiente de tu Python local)
3. F0 (Claude Code): crear modelos de `apps.tenants`, descomentar TENANT_MODEL/AUTH_USER_MODEL,
   y luego `migrate_schemas --shared`.

> El esqueleto NO migra de fábrica: faltan los modelos (apps.tenants.Tenant, accounts.Usuario).
> Eso lo implementa F0. Ver docs/PLAYBOOK_SAR_XENTY.md.
MD

# ─────────────────────────────────────────────────────────────────────────────
# venv + deps backend
# ─────────────────────────────────────────────────────────────────────────────
if [ "$DO_LOCAL_VENV" = 1 ]; then
  c_info "Creando venv LOCAL opcional ($PYTHON_BIN) — solo para IDE/tooling"
  PYV="$("$PYTHON_BIN" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "?")"
  [ "$PYV" != "3.12" ] && c_warn "Tu Python local es $PYV; el runtime del contenedor es 3.12. El venv local es solo conveniencia."
  set +e
  ( cd backend && "$PYTHON_BIN" -m venv .venv && . .venv/bin/activate && \
    pip install -q --upgrade pip && pip install -q -r requirements.txt )
  if [ $? -eq 0 ]; then c_ok "venv local listo (backend/.venv)"; else
    c_warn "Falló el venv local (Python $PYV puede ser incompatible con el stack). No pasa nada: el stack real corre en el contenedor."
  fi
  set -e
else
  c_info "Sin venv local (las dependencias se instalan en el contenedor con 'docker compose up --build')."
fi

# ─────────────────────────────────────────────────────────────────────────────
# Frontends (3 SPAs Vite + React + TS)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$DO_FRONTEND" = 1 ] && [ "$HAVE_NODE" = 1 ]; then
  c_info "Creando las 3 SPAs (Vite + React + TS)"
  for app in acceso proveedores admin; do
    npm create vite@latest "frontend-$app" -- --template react-ts >/dev/null 2>&1 \
      && c_ok "frontend-$app" \
      || c_warn "No se pudo crear frontend-$app (créala con: npm create vite@latest frontend-$app -- --template react-ts)"
  done
  c_warn "Falta instalar shadcn/ui, Tailwind, Zustand, Axios, React Router, Recharts en cada SPA (F0)."
elif [ "$DO_FRONTEND" = 1 ]; then
  c_warn "Sin Node: crea las SPAs luego con 'npm create vite@latest frontend-{acceso,proveedores,admin} -- --template react-ts'."
fi

# ─────────────────────────────────────────────────────────────────────────────
# Cierre
# ─────────────────────────────────────────────────────────────────────────────
c_ok "Esqueleto de '$PROJECT_DIR' listo."
cat <<NEXT

Siguientes pasos:
  1. Copia los 7 .md de la suite a $PROJECT_DIR/docs/
  2. cp .env.example .env  → genera SECRET_KEY y SECRET_KEY_FERNET (stdlib, corre en cualquier Python):
       python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(50)).decode())"   # SECRET_KEY
       python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"   # SECRET_KEY_FERNET
     (o dentro del contenedor: docker compose run --rm backend python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
  3. Coloca el código del SAR viejo como repo HERMANO (no dentro): ../_ref-sar-legacy
       y borra su carpeta temporal/ y su .git (secretos comprometidos — REMEDIACION §1).
  4. docker compose up --build        # instala deps en la imagen (Python 3.12) y levanta el stack
  5. Claude Code arranca F0 (PLAYBOOK_SAR_XENTY.md): modelos de apps.tenants, dos contextos JWT,
     MFA, billing sandbox, Mesa de Ayuda, shells React. Luego: migrate_schemas --shared.

Notas:
  - Tu Python local (p. ej. 3.14) NO afecta el runtime: la app corre en 3.12 dentro del contenedor.
  - El esqueleto NO migra de fábrica (faltan los modelos Tenant/Usuario: eso es F0).
NEXT