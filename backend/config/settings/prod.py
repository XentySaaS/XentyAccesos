from .base import *  # noqa: F401,F403

DEBUG = False
# HTTPS forzado en prod (security.W008). Gate por env: el superadmin-backend en dev corre sobre
# HTTP dentro de Docker y debe poder desactivarlo (SECURE_SSL_REDIRECT=False), sin debilitar prod.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True                        # elegible para la preload list (security.W021)
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Sentry con scrubbing de PII (REMEDIACION §A7) si SENTRY_DSN está presente.
if SENTRY_DSN:  # noqa: F405
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    from common.observability import scrub_event

    sentry_sdk.init(
        dsn=SENTRY_DSN,  # noqa: F405
        integrations=[DjangoIntegration()],
        before_send=scrub_event,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )
