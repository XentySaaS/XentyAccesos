@echo off
rem ===========================================================================
rem  bootstrap.bat - Esqueleto del monorepo "Xenty Acceso" (SAR sobre Xenty)
rem
rem  Equivalente Windows de bootstrap.sh. A DIFERENCIA del original, NO crea una
rem  carpeta nueva: genera todo el esqueleto en la MISMA carpeta donde vive este
rem  .bat (la raiz del proyecto). Las dependencias se instalan en el contenedor.
rem
rem  Uso:
rem    bootstrap.bat                 monta estructura + archivos en esta carpeta
rem    bootstrap.bat --local-venv    ADEMAS crea backend\.venv local (opcional)
rem    bootstrap.bat --no-frontend   omite las 3 SPAs
rem
rem  Implementacion: el header es batch puro (ASCII). El cuerpo real esta escrito
rem  en PowerShell despues del marcador y se ejecuta via PowerShell (presente en
rem  Windows 10/11). Esto preserva el contenido exacto de los archivos sin los
rem  problemas de escape de caracteres especiales propios de cmd.exe.
rem ===========================================================================
setlocal
set "BOOTSTRAP_ROOT=%~dp0"
set "BOOTSTRAP_ARGS=%*"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=Get-Content -Raw -Encoding UTF8 -LiteralPath '%~f0'; $m=[char]35+'==PS=='; $i=$s.IndexOf($m); iex $s.Substring($i+$m.Length)"
set "RC=%errorlevel%"
endlocal & exit /b %RC%
#==PS==
$ErrorActionPreference = 'Stop'

# --- raiz del proyecto (carpeta del .bat); NO se crea subcarpeta ------------
$root = $env:BOOTSTRAP_ROOT
if (-not $root) { $root = (Get-Location).Path }
$root = $root.TrimEnd('\')

# --- parseo de argumentos ----------------------------------------------------
$DO_LOCAL_VENV = $false
$DO_FRONTEND   = $true
$argList = @()
if ($env:BOOTSTRAP_ARGS) { $argList = ($env:BOOTSTRAP_ARGS -split '\s+') | Where-Object { $_ -ne '' } }
foreach ($a in $argList) {
  switch ($a) {
    '--local-venv'  { $DO_LOCAL_VENV = $true }
    '--no-frontend' { $DO_FRONTEND   = $false }
    '-h'     { Write-Host 'Uso: bootstrap.bat [--local-venv] [--no-frontend]'; exit 0 }
    '--help' { Write-Host 'Uso: bootstrap.bat [--local-venv] [--no-frontend]'; exit 0 }
    default  { Write-Host "Argumento no reconocido: $a" -ForegroundColor Yellow; exit 1 }
  }
}

function Info($m){ Write-Host ">> $m" -ForegroundColor Cyan }
function Ok($m)  { Write-Host "OK $m"  -ForegroundColor Green }
function Warn($m){ Write-Host "!  $m"  -ForegroundColor Yellow }

$utf8 = New-Object System.Text.UTF8Encoding($false)   # UTF-8 sin BOM

function Write-File($rel, $content){
  $full = Join-Path $root $rel
  $dir  = Split-Path $full -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  if (-not $content.EndsWith("`n")) { $content += "`n" }
  [System.IO.File]::WriteAllText($full, $content, $utf8)
}
function Make-Dir($rel){
  $full = Join-Path $root $rel
  if (-not (Test-Path $full)) { New-Item -ItemType Directory -Force -Path $full | Out-Null }
}
function Touch($rel){
  $full = Join-Path $root $rel
  $dir  = Split-Path $full -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  if (-not (Test-Path $full)) { [System.IO.File]::WriteAllText($full, '', $utf8) }
}

# --- preflight ---------------------------------------------------------------
Info "Verificando herramientas"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Warn "Docker no encontrado: lo necesitaras para correr el stack (docker compose up --build)."
}
$HAVE_NODE = [bool](Get-Command node -ErrorAction SilentlyContinue)
$HAVE_GIT  = [bool](Get-Command git  -ErrorAction SilentlyContinue)
$HAVE_PY   = [bool](Get-Command python -ErrorAction SilentlyContinue)
if ($DO_FRONTEND -and -not $HAVE_NODE) {
  Warn "Node no encontrado: se omitiran las SPAs (puedes correrlas luego)."
}
if ($DO_LOCAL_VENV -and -not $HAVE_PY) {
  Warn "Python no encontrado: se omitira el venv local (--local-venv)."
  $DO_LOCAL_VENV = $false
}

Info "Generando esqueleto en: $root"
if (Test-Path (Join-Path $root 'backend')) {
  Warn "'backend' ya existe en esta carpeta: se (re)generaran los archivos del esqueleto."
}
if ($HAVE_GIT -and -not (Test-Path (Join-Path $root '.git'))) {
  git -C "$root" init -q
  Ok "git init en la raiz"
}

# --- arbol base --------------------------------------------------------------
Info "Creando arbol de directorios"
Make-Dir 'backend/config/settings'
Make-Dir 'backend/config/middleware'
Make-Dir 'backend/apps'
Make-Dir 'backend/etl'
Make-Dir 'backend/tests'
Make-Dir 'docs'

# --- apps de negocio (MODELO_DATOS_SAR.md §4) --------------------------------
$APPS = @('tenants','accounts','proveedores','empleados','recintos','documentos',
          'eventos','citas','acceso','gafetes','sanciones','dispositivos',
          'mensajeria','cumplimiento','ocr','config','soporte')

foreach ($app in $APPS) {
  Make-Dir "backend/apps/$app/migrations"
  Touch "backend/apps/$app/__init__.py"
  Touch "backend/apps/$app/migrations/__init__.py"
  $appCap = $app.Substring(0,1).ToUpper() + $app.Substring(1)
  $appsPy = @"
from django.apps import AppConfig


class ${appCap}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.$app"
"@
  Write-File "backend/apps/$app/apps.py" $appsPy
  Write-File "backend/apps/$app/models.py" ('# Modelos de la app "' + $app + '" - implementar segun MODELO_DATOS_SAR.md')
  Write-File "backend/apps/$app/views.py" ''
  Write-File "backend/apps/$app/serializers.py" ''
  Write-File "backend/apps/$app/admin.py" ''
}
Touch 'backend/apps/__init__.py'
Ok ("Apps creadas: " + ($APPS -join ' '))

# --- manage.py + config ------------------------------------------------------
Info "Generando config/ y manage.py"

$manage = @'
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
'@
Write-File 'backend/manage.py' $manage

$cfgInit = @'
from .celery import app as celery_app

__all__ = ("celery_app",)
'@
Write-File 'backend/config/__init__.py' $cfgInit

$celery = @'
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("xenty_acceso")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# NOTA (F0): toda tarea que toque modelos TENANT_APPS debe envolverse en
# tenant_context(tenant). Ver CLAUDE.md §4 (Multitenancy).
'@
Write-File 'backend/config/celery.py' $celery

$asgi = @'
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_asgi_application()
'@
Write-File 'backend/config/asgi.py' $asgi

$wsgi = @'
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()
'@
Write-File 'backend/config/wsgi.py' $wsgi

$base = @'
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
'@
Write-File 'backend/config/settings/base.py' $base

$dev = @'
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="mailpit")  # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)  # noqa: F405
EMAIL_USE_TLS = False
'@
Write-File 'backend/config/settings/dev.py' $dev

$prod = @'
from .base import *  # noqa: F401,F403

DEBUG = False
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# F0: Sentry con scrubbing de PII (REMEDIACION §A7) si SENTRY_DSN está presente.
'@
Write-File 'backend/config/settings/prod.py' $prod

$ctrl = @'
"""Para el contenedor superadmin-backend: monta el URLconf público (schema 'public')."""
from .prod import *  # noqa: F401,F403

ROOT_URLCONF = "config.urls_public"
'@
Write-File 'backend/config/settings/control_plane.py' $ctrl

$urls = @'
"""Data plane — schema del tenant (por subdominio). F1+ monta las apps de negocio."""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("api/", include("apps.<app>.urls")),  # F1+
]
'@
Write-File 'backend/config/urls.py' $urls

$urlsPub = @'
"""Control plane — schema 'public'. F0 monta gestión de tenants, billing y webhooks Stripe."""
from django.urls import path

urlpatterns = [
    # path("api/tenants/", include("apps.tenants.urls")),       # F0
    # path("webhooks/stripe/", stripe_webhook_view),            # F0
]
'@
Write-File 'backend/config/urls_public.py' $urlsPub

Touch 'backend/config/middleware/__init__.py'
Touch 'backend/tests/__init__.py'
Write-File 'backend/etl/__init__.py' '# ETL MySQL→Postgres por tenant (F8). Ver MIGRACION_DATOS_SAR.md'

# --- dependencias del backend ------------------------------------------------
Info "Escribiendo requirements y pyproject"
$req = @'
Django==5.0.6
djangorestframework==3.15.1
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
'@
Write-File 'backend/requirements.txt' $req

$pyproj = @'
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.dev"
python_files = ["test_*.py", "*_test.py"]
'@
Write-File 'backend/pyproject.toml' $pyproj

$docker = @'
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
'@
Write-File 'backend/Dockerfile' $docker

# --- docker-compose + .env.example + .gitignore ------------------------------
Info "Generando docker-compose, .env.example y .gitignore"
$compose = @'
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
'@
Write-File 'docker-compose.yml' $compose

$envExample = @'
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
'@
Write-File '.env.example' $envExample

$gitignore = @'
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
'@
Write-File '.gitignore' $gitignore

$readme = @'
# Xenty Acceso

Reconstrucción del SAR (control de accesos) sobre el stack Xenty.
Esqueleto generado por `bootstrap.bat` (fase F0 del PLAYBOOK_SAR_XENTY.md).

## Documentación (en la raíz del proyecto)
PLAYBOOK_SAR_XENTY · CLAUDE · MODELO_DATOS_SAR · SAR_FUNCIONALIDADES ·
REMEDIACION_SEGURIDAD_SAR · MIGRACION_DATOS_SAR · PROMPT_CLAUDE_DESIGN_SAR

## Arranque rápido
1. `copy .env.example .env` y genera SECRET_KEY y SECRET_KEY_FERNET (ver salida de bootstrap.bat).
2. `docker compose up --build`  (deps en la imagen, Python 3.12 — independiente de tu Python local)
3. F0 (Claude Code): crear modelos de `apps.tenants`, descomentar TENANT_MODEL/AUTH_USER_MODEL,
   y luego `migrate_schemas --shared`.

> El esqueleto NO migra de fábrica: faltan los modelos (apps.tenants.Tenant, accounts.Usuario).
> Eso lo implementa F0. Ver PLAYBOOK_SAR_XENTY.md.
'@
Write-File 'README.md' $readme

# --- venv local opcional -----------------------------------------------------
if ($DO_LOCAL_VENV) {
  Info "Creando venv LOCAL opcional - solo para IDE/tooling"
  $pyv = (& python -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null)
  if ($pyv -ne '3.12') { Warn "Tu Python local es $pyv; el runtime del contenedor es 3.12. El venv local es solo conveniencia." }
  $venvPy = Join-Path $root 'backend\.venv\Scripts\python.exe'
  try {
    & python -m venv (Join-Path $root 'backend\.venv')
    & $venvPy -m pip install -q --upgrade pip
    & $venvPy -m pip install -q -r (Join-Path $root 'backend\requirements.txt')
    Ok "venv local listo (backend\.venv)"
  } catch {
    Warn "Fallo el venv local (Python $pyv puede ser incompatible con el stack). No pasa nada: el stack real corre en el contenedor."
  }
} else {
  Info "Sin venv local (las dependencias se instalan en el contenedor con 'docker compose up --build')."
}

# --- frontends (3 SPAs Vite + React + TS) ------------------------------------
if ($DO_FRONTEND -and $HAVE_NODE) {
  Info "Creando las 3 SPAs (Vite + React + TS)"
  foreach ($app in @('acceso','proveedores','admin')) {
    if (Test-Path (Join-Path $root "frontend-$app")) {
      Warn "frontend-$app ya existe: se omite."
      continue
    }
    try {
      Push-Location $root
      & npm create vite@latest "frontend-$app" -- --template react-ts | Out-Null
      Pop-Location
      Ok "frontend-$app"
    } catch {
      Pop-Location -ErrorAction SilentlyContinue
      Warn "No se pudo crear frontend-$app (creala con: npm create vite@latest frontend-$app -- --template react-ts)"
    }
  }
  Warn "Falta instalar shadcn/ui, Tailwind, Zustand, Axios, React Router, Recharts en cada SPA (F0)."
} elseif ($DO_FRONTEND) {
  Warn "Sin Node: crea las SPAs luego con 'npm create vite@latest frontend-{acceso,proveedores,admin} -- --template react-ts'."
}

# --- cierre ------------------------------------------------------------------
Ok "Esqueleto listo en: $root"
Write-Host ""
Write-Host "Siguientes pasos:"
Write-Host "  1. Los .md de la suite ya viven en esta carpeta (raiz)."
Write-Host "  2. copy .env.example .env  -> genera SECRET_KEY y SECRET_KEY_FERNET (stdlib, cualquier Python):"
Write-Host '       python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(50)).decode())"   # SECRET_KEY'
Write-Host '       python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"   # SECRET_KEY_FERNET'
Write-Host '     (o en el contenedor: docker compose run --rm backend python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")'
Write-Host "  3. Coloca el codigo del SAR viejo como repo HERMANO (no dentro): ..\_ref-sar-legacy"
Write-Host "       y borra su carpeta temporal\ y su .git (secretos comprometidos - REMEDIACION §1)."
Write-Host "  4. docker compose up --build        # instala deps en la imagen (Python 3.12) y levanta el stack"
Write-Host "  5. Claude Code arranca F0 (PLAYBOOK_SAR_XENTY.md): modelos de apps.tenants, dos contextos JWT,"
Write-Host "     MFA, billing sandbox, Mesa de Ayuda, shells React. Luego: migrate_schemas --shared."
Write-Host ""
Write-Host "Notas:"
Write-Host "  - Tu Python local NO afecta el runtime: la app corre en 3.12 dentro del contenedor."
Write-Host "  - El esqueleto NO migra de fabrica (faltan los modelos Tenant/Usuario: eso es F0)."
exit 0
