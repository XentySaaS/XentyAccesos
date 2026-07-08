from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# El correo transaccional (incl. Mailpit en dev) se configura en base.py, compartido con el
# control plane (donde corre el signup). Aquí no se redefine para no divergir.
