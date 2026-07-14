"""Control plane (schema public): alta self-service de tenants + administración del super-admin."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import ProtectedError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auth_api import BaseLoginView
from common.jwt import build_tokens
from common.permissions import EsSuperAdmin, MFASesionCompleta

from .models import ConfiguracionConnector, Plan, SaldoCreditos, SuperAdmin, Tenant
from .services import billing
from .services.provisioning import ProvisionError, provisionar_tenant
from .services.stripe_gateway import crear_checkout_suscripcion


# ── Auth del super-admin ─────────────────────────────────────────────────────
class _CredencialesSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="post")
class SuperAdminLoginView(BaseLoginView):
    """Login del super-admin con MFA obligatorio.

    Además de los tokens, informa al SPA si debe **enrolar** el 2º factor o solo **verificarlo**:
    - ``mfa_pendiente``: la sesión aún no completa el 2º factor (token ``mfa="pending"``).
    - ``mfa_enrolar``:  pendiente **y** sin ningún factor enrolado (ni TOTP ni passkey) → el SPA
      debe mostrar el enrolamiento (QR) en vez del campo de código.
    """

    model = SuperAdmin
    ctx = "superadmin"

    def post(self, request):
        s = _CredencialesSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        invalidas = Response({"detail": "Credenciales inválidas."}, status=401)
        try:
            actor = SuperAdmin.objects.get(email=s.validated_data["email"].lower())
        except SuperAdmin.DoesNotExist:
            return invalidas
        if not actor.check_password(s.validated_data["password"]) or not actor.is_active:
            return invalidas
        pendiente = bool(actor.mfa_habilitado)
        enrolado = bool(actor.mfa_totp_secret) or actor.credenciales_webauthn.exists()
        data = build_tokens(actor, self.ctx, mfa_pendiente=pendiente)
        data["mfa_pendiente"] = pendiente
        data["mfa_enrolar"] = pendiente and not enrolado
        return Response(data)


# ── Alta pública self-service de tenants ─────────────────────────────────────
class SignupSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=200)  # razón comercial
    subdominio = serializers.SlugField(max_length=31)
    admin_email = serializers.EmailField()
    admin_nombre = serializers.CharField(max_length=160)
    admin_password = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)
    plan = serializers.CharField(required=False, allow_blank=True)


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True), name="post")
class SignupView(APIView):
    """POST /api/signup/ — alta pública: aprovisiona el tenant completo y su admin."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        s = SignupSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        slug = d["subdominio"].lower()
        dominio = f"{slug}.{settings.TENANT_BASE_DOMAIN}"
        try:
            tenant, _ = provisionar_tenant(
                slug=slug,
                dominio=dominio,
                nombre=d["nombre"],
                admin_email=d["admin_email"],
                admin_nombre=d["admin_nombre"],
                admin_password=d["admin_password"],
                plan_clave=d.get("plan") or None,
                verificar_email=False,  # alta pública: doble opt-in por correo
            )
        except ProvisionError as exc:
            return Response({"detail": str(exc)}, status=400)

        # Doble opt-in: enviar enlace de verificación al correo del admin (en su schema de tenant).
        from django_tenants.utils import schema_context

        from apps.accounts.models import Usuario
        from common.email_verify import build_verify_url, generar_token
        from common.emails import enviar_verificacion_email

        with schema_context(slug):
            admin = Usuario.objects.get(email=d["admin_email"].lower())
            token = generar_token(admin, "acceso")
            admin_telefono = admin.telefono
        enviar_verificacion_email(
            email_destino=d["admin_email"],
            nombre=d["admin_nombre"],
            nombre_tenant=d["nombre"],
            url=build_verify_url(request, slug, token),
            telefono=admin_telefono,
        )
        return Response(
            {
                "tenant": tenant.schema_name,
                "dominio": dominio,
                "estado": tenant.estado,
                "verificacion_requerida": True,
                "detail": "Registro creado. Revisa tu correo para confirmar tu cuenta.",
            },
            status=201,
        )


# ── Administración de tenants (super-admin) ──────────────────────────────────
class TenantAdminSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()
    saldo = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "id",
            "schema_name",
            "nombre",
            "estado",
            "trial_ends_at",
            "modo_solo_lectura",
            "gracia_hasta",
            "plan",
            "saldo",
        ]

    def get_plan(self, obj):
        return obj.plan.clave if obj.plan_id else None

    def get_saldo(self, obj) -> int:
        s = SaldoCreditos.objects.filter(tenant=obj).first()
        return s.saldo if s else 0


class AsignarPlanSerializer(serializers.Serializer):
    # Clave del plan a asignar; null/"" desasigna (deja el tenant sin plan).
    plan = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class OtorgarGraciaSerializer(serializers.Serializer):
    # Días de gracia desde ahora. 0 (o negativo) revoca la gracia vigente.
    dias = serializers.IntegerField(min_value=0, max_value=365)


class AcreditarCreditosSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField()  # + acredita / - ajuste
    motivo = serializers.CharField(max_length=160)

    def validate_cantidad(self, v: int) -> int:
        if v == 0:
            raise serializers.ValidationError("La cantidad no puede ser cero.")
        return v


class TenantAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista y administra TODOS los tenants (suspender/activar/cancelar)."""

    queryset = Tenant.objects.all().order_by("schema_name")
    serializer_class = TenantAdminSerializer
    permission_classes = [IsAuthenticated, MFASesionCompleta, EsSuperAdmin]
    filterset_fields = ["estado"]

    def _accion(self, fn):
        tenant = self.get_object()
        fn(tenant)
        tenant.refresh_from_db()
        return Response(self.get_serializer(tenant).data)

    @action(detail=True, methods=["post"])
    def suspender(self, request, pk=None):
        return self._accion(billing.suspender)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        return self._accion(billing.activar)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        return self._accion(billing.cancelar)

    @action(detail=True, methods=["post"], url_path="asignar-plan")
    def asignar_plan(self, request, pk=None):
        """Asigna (o desasigna) el plan del tenant. No crea suscripción Stripe: solo fija el plan
        que gobierna los módulos disponibles y el checkout por defecto."""
        tenant = self.get_object()
        s = AsignarPlanSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        clave = s.validated_data.get("plan")
        if clave:
            plan = Plan.objects.filter(clave=clave).first()
            if plan is None:
                return Response({"detail": "Plan no encontrado."}, status=404)
            tenant.plan = plan
        else:
            tenant.plan = None
        tenant.save(update_fields=["plan"])
        tenant.refresh_from_db()
        return Response(self.get_serializer(tenant).data)

    @action(detail=True, methods=["post"], url_path="otorgar-gracia")
    def otorgar_gracia(self, request, pk=None):
        """Concede N días de acceso manual (pago externo) desde ahora. ``dias=0`` revoca la gracia."""
        tenant = self.get_object()
        s = OtorgarGraciaSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        dias = s.validated_data["dias"]
        tenant.gracia_hasta = timezone.now() + timedelta(days=dias) if dias > 0 else None
        tenant.save(update_fields=["gracia_hasta"])
        tenant.refresh_from_db()
        return Response(self.get_serializer(tenant).data)

    @action(detail=True, methods=["post"])
    def creditos(self, request, pk=None):
        """Acredita (o ajusta) créditos del tenant y registra el movimiento en el ledger."""
        tenant = self.get_object()
        s = AcreditarCreditosSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        billing.acreditar_creditos(
            tenant,
            s.validated_data["cantidad"],
            s.validated_data["motivo"],
            referencia=f"admin:{request.user.pk}",
        )
        tenant.refresh_from_db()
        return Response(self.get_serializer(tenant).data)

    # ── Verificación de correo del admin del tenant ──────────────────────────
    # El admin del tenant (accounts.Usuario) vive en el schema del tenant; estas acciones entran a
    # su schema. Sirven cuando el correo de doble opt-in no llega y el admin queda bloqueado por el
    # permiso EmailVerificado.
    def _admins(self, tenant, *, solo_pendientes=False):
        from apps.accounts.models import Usuario

        qs = Usuario.objects.filter(rol=Usuario.Rol.ADMINISTRADOR, activo=True)
        if solo_pendientes:
            qs = qs.filter(email_verificado__isnull=True)
        return qs.order_by("id")

    @action(detail=True, methods=["get"])
    def verificacion(self, request, pk=None):
        """Estado de verificación de correo de los administradores del tenant."""
        from django_tenants.utils import schema_context

        tenant = self.get_object()
        with schema_context(tenant.schema_name):
            admins = [
                {"email": u.email, "nombre": u.nombre, "verificado": u.email_verificado is not None}
                for u in self._admins(tenant)
            ]
        return Response({"administradores": admins})

    @action(detail=True, methods=["post"], url_path="reenviar-verificacion")
    def reenviar_verificacion(self, request, pk=None):
        """Reenvía el correo de verificación a los administradores con el correo pendiente."""
        from django_tenants.utils import schema_context

        from common.email_verify import build_verify_url, generar_token
        from common.emails import enviar_verificacion_email

        tenant = self.get_object()
        with schema_context(tenant.schema_name):
            pendientes = [
                (u.email, u.nombre, generar_token(u, "acceso"), u.telefono)
                for u in self._admins(tenant, solo_pendientes=True)
            ]
        for email, nombre, token, telefono in pendientes:
            enviar_verificacion_email(
                email_destino=email,
                nombre=nombre,
                nombre_tenant=tenant.nombre,
                url=build_verify_url(request, tenant.schema_name, token),
                telefono=telefono,
            )
        return Response(
            {
                "reenviados": [e for e, *_ in pendientes],
                "detail": (
                    f"Correo de verificación reenviado a {len(pendientes)} administrador(es)."
                    if pendientes
                    else "No hay administradores con el correo pendiente de verificar."
                ),
            }
        )

    @action(detail=True, methods=["post"], url_path="verificar-email")
    def verificar_email(self, request, pk=None):
        """Marca como verificado el correo de los admins pendientes (fallback sin correo)."""
        from django_tenants.utils import schema_context

        tenant = self.get_object()
        verificados = []
        with schema_context(tenant.schema_name):
            from apps.config.models import HistorialCambio

            for u in self._admins(tenant, solo_pendientes=True):
                u.email_verificado = timezone.now()
                u.save(update_fields=["email_verificado"])
                verificados.append(u.email)
                try:
                    HistorialCambio.objects.create(
                        descripcion=f"Super-admin verificó manualmente el correo de {u.email}",
                        modelo="accounts.Usuario",
                        modelo_id=u.pk,
                        usuario=None,  # el actor es super-admin (control plane), no un Usuario
                        accion="actualizado",
                    )
                except Exception:  # noqa: BLE001 — la auditoría no debe tumbar la acción
                    pass
        return Response(
            {
                "verificados": verificados,
                "detail": (
                    f"Correo verificado manualmente para {len(verificados)} administrador(es)."
                    if verificados
                    else "No hay administradores con el correo pendiente de verificar."
                ),
            }
        )


class PlanAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "clave",
            "nombre",
            "descripcion",
            "precio_mensual",
            "stripe_price_id",
            "modulos",
            "limites",
            "activo",
        ]


class PlanAdminViewSet(viewsets.ModelViewSet):
    """CRUD de planes comerciales (super-admin). ``clave`` es estable: no reasignar a la ligera."""

    queryset = Plan.objects.all().order_by("precio_mensual", "id")
    serializer_class = PlanAdminSerializer
    permission_classes = [IsAuthenticated, MFASesionCompleta, EsSuperAdmin]
    filterset_fields = ["activo"]

    def destroy(self, request, *args, **kwargs):
        # Suscripcion.plan es PROTECT: si hay suscripciones, no se puede borrar → 409 con guía.
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": "No se puede eliminar: hay suscripciones que usan este plan. "
                    "Desactívalo en su lugar."
                },
                status=status.HTTP_409_CONFLICT,
            )


# ── Comunicaciones: config global del Connector (XCC) ────────────────────────
class ConfiguracionConnectorSerializer(serializers.ModelSerializer):
    # El secreto HMAC es write-only: entra para guardarse (cifrado) y jamás se devuelve en claro.
    hmac_secret = serializers.CharField(
        required=False, allow_blank=True, write_only=True, trim_whitespace=False
    )
    hmac_configurado = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracionConnector
        fields = [
            "habilitado",
            "url_base",
            "hmac_secret",
            "hmac_configurado",
            "timeout_ms",
            "intervalo_health",
            "reintentos_default",
            "estrategia_failover",
            "cb_umbral",
            "cb_cooldown",
            "cb_ventana",
            "recuperacion_automatica",
            "actualizado",
        ]
        read_only_fields = ["actualizado"]

    def get_hmac_configurado(self, obj) -> bool:
        return bool(obj.hmac_secret)

    def update(self, instance, validated_data):
        # Un hmac_secret vacío NO borra el existente (misma semántica que api_key en Mesa).
        if not validated_data.get("hmac_secret"):
            validated_data.pop("hmac_secret", None)
        return super().update(instance, validated_data)


class ConfiguracionConnectorView(APIView):
    """GET/PUT /api/admin/comunicaciones/ — config global del Connector (master switch + failover)."""

    permission_classes = [IsAuthenticated, MFASesionCompleta, EsSuperAdmin]

    def get(self, request):
        cfg = ConfiguracionConnector.cargar()
        return Response(ConfiguracionConnectorSerializer(cfg).data)

    def put(self, request):
        cfg = ConfiguracionConnector.cargar()
        s = ConfiguracionConnectorSerializer(cfg, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        # Propaga el cambio al Router de inmediato (invalida su snapshot cacheado).
        from django.core.cache import cache

        cache.delete("connector:config")
        return Response(ConfiguracionConnectorSerializer(cfg).data)


class CrearCheckoutView(APIView):
    """POST /api/admin/tenants/<id>/checkout/ — sesión de checkout de suscripción del tenant."""

    permission_classes = [IsAuthenticated, MFASesionCompleta, EsSuperAdmin]

    def post(self, request, tenant_id):
        tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant is None:
            return Response({"detail": "Tenant no encontrado."}, status=404)
        plan = tenant.plan or Plan.objects.filter(activo=True).order_by("id").first()
        if plan is None:
            return Response({"detail": "No hay un plan disponible."}, status=400)
        return Response(crear_checkout_suscripcion(tenant, plan))
