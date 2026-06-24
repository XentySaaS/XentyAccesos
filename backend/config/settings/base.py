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
# Allowlist de IPs para /admin/ (RestringirAdminPorIP). Vacío = sin restricción (dev).
ADMIN_IP_ALLOWLIST = config("ADMIN_IP_ALLOWLIST", default="", cast=Csv())

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
    "django_tenants.middleware.main.TenantMainMiddleware",          # 1. resuelve request.tenant
    "config.middleware.enforcement.RestringirAdminPorIP",           # 2. /admin/ por IP
    "config.middleware.enforcement.EnforceMantenimiento",           # 3. 503 en mantenimiento
    "config.middleware.enforcement.BloquearTenantsInactivos",       # 4. suspendido/cancelado
    # Slot 5 (email no verificado) -> common.permissions.EmailVerificado (DRF, requiere actor JWT)
    "config.middleware.enforcement.BloquearTrialExpirado",          # 6. trial vencido
    "config.middleware.enforcement.EnforceModoSoloLectura",         # 7. 423 en dunning
    # Slot 9 (sesión MFA incompleta) -> common.permissions.MFASesionCompleta (DRF)
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
# El proveedor (apps.proveedores.CuentaProveedor) y el super-admin (apps.tenants.SuperAdmin) son
# authenticatables SEPARADOS con su propio flujo JWT (CLAUDE.md §4); no son AUTH_USER_MODEL.
AUTH_USER_MODEL = "accounts.Usuario"

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
        # Resuelve el actor por contexto (acceso/proveedores) y valida pertenencia al tenant.
        "common.jwt.TenantAwareJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "common.permissions.MFASesionCompleta",   # §6 slot 9: sesión MFA incompleta -> 403
        "common.permissions.EmailVerificado",     # §6 slot 5: email no verificado -> 403
    ),
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
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")   # firma del webhook (prod)
STRIPE_SUCCESS_URL = config("STRIPE_SUCCESS_URL", default="https://app.xenty.mx/billing/ok")
STRIPE_CANCEL_URL = config("STRIPE_CANCEL_URL", default="https://app.xenty.mx/billing/cancel")
ULTRAMSG_TOKEN = config("ULTRAMSG_TOKEN", default="")
ULTRAMSG_INSTANCE_ID = config("ULTRAMSG_INSTANCE_ID", default="")
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION = config("AWS_REGION", default="us-east-1")
SAT_EFOS_UPDATE_EVERY_MONTHS = config("SAT_EFOS_UPDATE_EVERY_MONTHS", default=1, cast=int)
SAT_EFOS_CSV_URL = config("SAT_EFOS_CSV_URL", default="")
SAT_EFOS_ESTATUS_BLOQUEANTES = config(
    "SAT_EFOS_ESTATUS_BLOQUEANTES", default="Definitivo,Presunto", cast=Csv()
)
SENTRY_DSN = config("SENTRY_DSN", default="")
