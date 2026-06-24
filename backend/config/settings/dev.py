from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="mailpit")  # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)  # noqa: F405
EMAIL_USE_TLS = False
