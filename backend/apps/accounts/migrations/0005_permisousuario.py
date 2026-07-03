import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_usuario_actualizado_usuario_creado"),
    ]

    operations = [
        migrations.CreateModel(
            name="PermisoUsuario",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "modulo",
                    models.CharField(
                        choices=[
                            ("eventos", "Eventos"),
                            ("citas", "Citas"),
                            ("acceso", "Acceso"),
                            ("recintos", "Recintos"),
                            ("proveedores", "Proveedores"),
                            ("sanciones", "Sanciones"),
                            ("mensajeria", "Mensajería"),
                            ("verificacion", "Verificación"),
                        ],
                        max_length=30,
                    ),
                ),
                ("ver", models.BooleanField(default=True)),
                ("crear", models.BooleanField(default=False)),
                ("editar", models.BooleanField(default=False)),
                ("eliminar", models.BooleanField(default=False)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permisos_modulos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "permiso personalizado",
                "verbose_name_plural": "permisos personalizados",
            },
        ),
        migrations.AlterUniqueTogether(
            name="permisousuario",
            unique_together={("usuario", "modulo")},
        ),
    ]
