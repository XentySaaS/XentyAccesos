"""Vistas de proveedores: CRUD + invitación (admin) y onboarding público (token firmado)."""

from __future__ import annotations

from django.core import signing
from django.db import connection
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django_tenants.utils import schema_context
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.config.services import AuditViewSetMixin
from common.emails import enviar_activacion_proveedor, enviar_invitacion_proveedor
from common.permissions import PERMISOS_BASE, RequiereModulo, RequiereRol
from common.signing import VIGENCIA_HORAS, firmar_invitacion, leer_invitacion

from .models import CuentaProveedor, Proveedor
from .serializers import OnboardingProveedorSerializer, ProveedorSerializer


def _base_url_de(request) -> str:
    """URL base (scheme+host) de la petición del admin.

    El admin invita desde ``<tenant>.dominio`` (subdominio del tenant), así el link de onboarding
    hereda ese host y Nginx preserva el Host → django-tenants resuelve el tenant. Es lo que evita el
    404 "No tenant for hostname" que aparece al apuntar a un host sin contexto de tenant.
    """
    return f"{request.scheme}://{request.get_host()}"


class ProveedorViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Proveedor.objects.all().order_by("id")
    serializer_class = ProveedorSerializer
    permission_classes = [
        *PERMISOS_BASE(),
        RequiereModulo("proveedores"),
        RequiereRol("administrador"),
    ]
    filterset_fields = ["estado", "rfc"]

    def perform_create(self, serializer):
        """Guarda el proveedor, registra la verificación 69-B y envía la invitación."""
        super().perform_create(serializer)
        proveedor = serializer.instance
        # Audita la consulta a la lista 69-B (el bloqueo ya se aplicó al validar el RFC).
        try:
            from apps.cumplimiento.services import validar_69b

            validar_69b(proveedor)
        except Exception:  # noqa: BLE001 — auditoría best-effort
            pass
        email_destino = proveedor.email_responsable or proveedor.email
        if email_destino:
            token = firmar_invitacion(proveedor.id, connection.schema_name)
            nombre_tenant = getattr(self.request.tenant, "nombre", connection.schema_name)
            enviar_invitacion_proveedor(
                email_destino=email_destino,
                nombre_empresa=proveedor.nombre,
                nombre_tenant=nombre_tenant,
                token=token,
                base_url=_base_url_de(self.request),
                telefono=proveedor.telefono,
            )

    def perform_destroy(self, instance):
        """Solo se pueden eliminar proveedores en estado pendiente (sin cuenta ni datos)."""
        if instance.estado != Proveedor.Estado.PENDIENTE:
            raise ValidationError(
                "Solo puedes eliminar proveedores en estado pendiente. "
                "Para uno confirmado o activo, desactívalo."
            )
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def invitar(self, request, pk=None):
        """Genera token de invitación (72h) y lo envía por correo al responsable."""
        proveedor = self.get_object()
        token = firmar_invitacion(proveedor.id, connection.schema_name)

        email_destino = proveedor.email_responsable or proveedor.email
        if email_destino:
            nombre_tenant = getattr(request.tenant, "nombre", connection.schema_name)
            enviar_invitacion_proveedor(
                email_destino=email_destino,
                nombre_empresa=proveedor.nombre,
                nombre_tenant=nombre_tenant,
                token=token,
                base_url=_base_url_de(request),
                telefono=proveedor.telefono,
            )

        return Response(
            {
                "token": token,
                "vigencia_horas": VIGENCIA_HORAS,
                "email_enviado": bool(email_destino),
                "onboarding_url": f"{_base_url_de(request)}/proveedores/onboarding?token={token}",
            }
        )

    @action(detail=True, methods=["get"])
    def revision(self, request, pk=None):
        """Documentos del onboarding para que el admin los revise antes de activar.

        Devuelve qué documentos existen (no las rutas crudas) y los datos del responsable
        para cotejar identidad. Los archivos se descargan por la acción ``documento`` (con auth).
        """
        proveedor = self.get_object()
        resp = proveedor.responsable
        return Response(
            {
                "empresa": {
                    "nombre": proveedor.nombre,
                    "razon_social": proveedor.razon_social,
                    "rfc": proveedor.rfc,
                    "repse": bool(proveedor.file_repse),
                    "sua": bool(proveedor.file_sua),
                },
                "responsable": (
                    {
                        "nombre": f"{resp.nombre} {resp.apellidos or ''}".strip(),
                        "email": resp.email,
                        "puesto": resp.puesto,
                        "curp": resp.curp,  # PII descifrada solo para cotejo del admin
                        "nss": resp.nss,
                        "ine": bool(resp.file_ine),
                        "foto": bool(resp.foto),
                    }
                    if resp
                    else {
                        "nombre": proveedor.nombre_responsable,
                        "email": proveedor.email_responsable,
                        "puesto": None,
                        "curp": None,
                        "nss": None,
                        "ine": False,
                        "foto": False,
                    }
                ),
                "estado": proveedor.estado,
            }
        )

    @action(detail=True, methods=["get"])
    def documento(self, request, pk=None):
        """Sirve un documento del onboarding con auth de admin (sin ruta cruda).

        ``?tipo=`` ∈ {repse, sua, ine, foto}. El servidor mapea el tipo a un campo concreto;
        el cliente nunca pasa rutas. La pertenencia queda garantizada por el schema del tenant.
        """
        proveedor = self.get_object()
        tipo = request.query_params.get("tipo", "")
        resp = proveedor.responsable
        archivo = {
            "repse": proveedor.file_repse,
            "sua": proveedor.file_sua,
            "ine": resp.file_ine if resp else None,
            "foto": resp.foto if resp else None,
        }.get(tipo)
        if not archivo:
            raise Http404("Documento no disponible.")
        return FileResponse(archivo.open("rb"))

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """Activa el proveedor (CONFIRMADO → ACTIVO) y notifica al responsable."""
        proveedor = self.get_object()
        if proveedor.estado == Proveedor.Estado.ACTIVO:
            return Response(
                {"detail": "El proveedor ya está activo."}, status=status.HTTP_400_BAD_REQUEST
            )

        proveedor.estado = Proveedor.Estado.ACTIVO
        proveedor.save(update_fields=["estado"])

        cuenta = proveedor.responsable
        if cuenta and cuenta.email:
            nombre_tenant = getattr(request.tenant, "nombre", connection.schema_name)
            enviar_activacion_proveedor(
                email_destino=cuenta.email,
                nombre_responsable=cuenta.nombre,
                nombre_empresa=proveedor.nombre,
                nombre_tenant=nombre_tenant,
                base_url=_base_url_de(request),
                telefono=getattr(cuenta, "telefono", None) or proveedor.telefono,
            )

        return Response(
            {
                "detail": "Proveedor activado.",
                "estado": proveedor.estado,
                "email_enviado": bool(cuenta and cuenta.email),
            }
        )

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """Desactiva el proveedor (estado → INACTIVO)."""
        proveedor = self.get_object()
        proveedor.estado = Proveedor.Estado.INACTIVO
        proveedor.save(update_fields=["estado"])
        return Response({"detail": "Proveedor desactivado.", "estado": proveedor.estado})


@method_decorator(ratelimit(key="ip", rate="20/h", method="POST", block=True), name="post")
class OnboardingProveedorView(APIView):
    """Onboarding público del proveedor mediante invitación firmada.

    Funciona desde el schema público (localhost en dev) Y desde el schema de tenant
    (subdominio en prod), porque usa schema_context para cambiar al schema correcto
    según el tenant que viene en el token.

    GET  ?token=…   → devuelve datos del proveedor para pre-rellenar el wizard.
    POST            → procesa el wizard completo (multipart/form-data).
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def _leer_token(self, token_str: str):
        """Valida el token y devuelve (payload, tenant_slug). Lanza Response en error."""
        if not token_str:
            raise ValueError("Token requerido.")
        payload = leer_invitacion(token_str)  # lanza SignatureExpired / BadSignature
        tenant_slug = payload.get("tenant", "")
        if not tenant_slug:
            raise signing.BadSignature("Token sin tenant.")
        return payload, tenant_slug

    # ── GET: pre-fill del wizard ─────────────────────────────────────────────
    def get(self, request):
        token_str = request.query_params.get("token", "")
        try:
            payload, tenant_slug = self._leer_token(token_str)
        except ValueError:
            return Response({"detail": "Token requerido."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.SignatureExpired:
            return Response({"detail": "La invitación expiró."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return Response({"detail": "Invitación inválida."}, status=status.HTTP_400_BAD_REQUEST)

        with schema_context(tenant_slug):
            proveedor = Proveedor.objects.filter(pk=payload.get("proveedor_id")).first()
            if proveedor is None:
                return Response(
                    {"detail": "El proveedor ya no existe."}, status=status.HTTP_404_NOT_FOUND
                )
            if proveedor.estado in (Proveedor.Estado.CONFIRMADO, Proveedor.Estado.ACTIVO):
                return Response(
                    {"detail": "Este proveedor ya completó el registro.", "ya_registrado": True},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {
                    "nombre": proveedor.nombre,
                    "razon_social": proveedor.razon_social or "",
                    "rfc": proveedor.rfc or "",
                    "email_empresa": proveedor.email or "",
                    "telefono_empresa": proveedor.telefono or "",
                    "nombre_responsable": proveedor.nombre_responsable or "",
                    "email_responsable": proveedor.email_responsable or "",
                }
            )

    # ── POST: procesamiento completo del wizard ──────────────────────────────
    def post(self, request):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data.update(request.FILES)

        s = OnboardingProveedorSerializer(data=data)
        s.is_valid(raise_exception=True)
        datos = s.validated_data

        try:
            payload, tenant_slug = self._leer_token(datos["token"])
        except ValueError:
            return Response({"detail": "Token requerido."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.SignatureExpired:
            return Response({"detail": "La invitación expiró."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return Response({"detail": "Invitación inválida."}, status=status.HTTP_400_BAD_REQUEST)

        with schema_context(tenant_slug):
            proveedor = Proveedor.objects.filter(pk=payload.get("proveedor_id")).first()
            if proveedor is None:
                return Response(
                    {"detail": "El proveedor ya no existe."}, status=status.HTTP_404_NOT_FOUND
                )

            # Paso 1: actualizar empresa
            campos_empresa: list[str] = []
            if datos.get("email_empresa"):
                proveedor.email = datos["email_empresa"]
                campos_empresa.append("email")
            if datos.get("telefono_empresa"):
                proveedor.telefono = datos["telefono_empresa"]
                campos_empresa.append("telefono")
            if datos.get("repse"):
                proveedor.file_repse = datos["repse"]
                campos_empresa.append("file_repse")
            if datos.get("sua"):
                proveedor.file_sua = datos["sua"]
                campos_empresa.append("file_sua")
            if campos_empresa:
                proveedor.save(update_fields=campos_empresa)

            # Paso 2+3: crear CuentaProveedor
            kwargs_cuenta: dict = {}
            if datos.get("curp"):
                kwargs_cuenta["curp"] = datos["curp"]
            if datos.get("nss"):
                kwargs_cuenta["nss"] = datos["nss"]

            cuenta = CuentaProveedor.objects.create_user(
                email=datos["email"],
                nombre=datos["nombre"],
                password=datos["password"],
                apellidos=datos.get("apellidos") or "",
                puesto=datos.get("puesto") or "",
                telefono=datos.get("whatsapp") or "",
                proveedor=proveedor,
                rol=CuentaProveedor.Rol.ADMIN,
                # El onboarding se hizo vía un enlace firmado enviado a su correo: eso prueba la
                # propiedad del email, así que la cuenta queda verificada y puede usar el portal.
                email_verificado=timezone.now(),
                **kwargs_cuenta,
            )

            campos_cuenta: list[str] = []
            if datos.get("file_ine"):
                cuenta.file_ine = datos["file_ine"]
                campos_cuenta.append("file_ine")
            if datos.get("foto"):
                cuenta.foto = datos["foto"]
                campos_cuenta.append("foto")
            if campos_cuenta:
                cuenta.save(update_fields=campos_cuenta)

            if proveedor.responsable_id is None:
                proveedor.responsable = cuenta
            proveedor.estado = Proveedor.Estado.CONFIRMADO
            proveedor.save(update_fields=["responsable", "estado"])

        return Response({"detail": "Alta completada.", "proveedor": proveedor.id}, status=201)
