from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documentos", "0002_documentoempleado_actualizado_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Protocolo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=200)),
                ("descripcion", models.TextField(blank=True, null=True)),
                ("archivo", models.FileField(blank=True, null=True, upload_to="protocolos/")),
                ("estado", models.CharField(
                    choices=[("activo", "Activo"), ("inactivo", "Inactivo")],
                    default="activo",
                    max_length=10,
                )),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("actualizado", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
