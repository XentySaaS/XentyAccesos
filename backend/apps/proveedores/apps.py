from django.apps import AppConfig


class ProveedoresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.proveedores"

    def ready(self):  # señales de sincronización del DirectorioProveedor (hub de login)
        from . import signals  # noqa: F401
