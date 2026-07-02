# Contexto del Proyecto — Xenty Acceso

> Para stack, reglas y convenciones detalladas → `CLAUDE.md` (raíz del repo).
> Este archivo complementa CLAUDE.md con orientación rápida y mapa de archivos.

## Qué es

SaaS multitenant de control de accesos a recintos (estadios, museos, plantas industriales). Tercer producto de la suite Xenty (junto a XentyFiscal y XentyNominayRH). Reconstrucción desde Laravel/Filament/MySQL al stack oficial Xenty (Django/DRF/django-tenants/PostgreSQL/React).

## Cómo ejecutar

```bash
# Levantar todo
docker compose up -d

# Acceder (dev)
# Frontend acceso:      http://demo.localhost:8080  (vía Nginx)
# Frontend proveedores: http://demo.localhost:8080  (puerto Vite: 5174)
# Backend directo:      http://localhost:8002/api/
# Admin Django:         http://localhost:8002/admin/

# Migraciones (SIEMPRE así, nunca "migrate" a secas)
docker compose exec backend python manage.py migrate_schemas --shared
docker compose exec backend python manage.py migrate_schemas --tenant

# Backend usa --noreload: cada cambio .py requiere:
docker compose restart backend
```

## Dónde encontrar las cosas

| Necesito... | Buscar en... |
|---|---|
| Modelos de un módulo | `backend/apps/{modulo}/models.py` |
| ViewSets / endpoints | `backend/apps/{modulo}/views.py` |
| Serializers | `backend/apps/{modulo}/serializers.py` |
| URLs de un módulo | `backend/apps/{modulo}/urls.py` |
| Permisos (RequiereRol, etc.) | `backend/common/permissions.py` |
| Auditoría (registrar, AuditViewSetMixin) | `backend/apps/config/services.py` |
| Gafetes QR (diseño + emisión) | `backend/apps/gafetes/services.py` |
| Auth JWT custom | `backend/common/auth_api.py` |
| Crypto Fernet | `backend/common/crypto.py` |
| Validadores de archivos | `backend/common/validators.py` |
| Settings | `backend/config/settings/{base,dev,prod,control_plane}.py` |
| URLs data plane | `backend/config/urls.py` |
| URLs control plane | `backend/config/urls_public.py` |
| Frontend acceso (páginas) | `frontend-acceso/src/pages/` |
| Frontend proveedores (páginas) | `frontend-proveedores/src/pages/` |
| Frontend admin (páginas) | `frontend-admin/src/pages/` |
| API client (Axios + interceptors) | `frontend-*/src/api/client.ts` |
| Auth store (Zustand) | `frontend-*/src/store/auth.ts` |
| Documentación del dominio | `docs/` |

## Patrones clave

1. **Permisos**: siempre `permission_classes = [*PERMISOS_BASE(), ContextoX, RequiereRol(...), RequierePermisoPersonalizado(...)]`
2. **Auditoría**: heredar `AuditViewSetMixin` antes de `ModelViewSet`
3. **MultiPartParser**: agregar `parser_classes = [JSONParser, MultiPartParser, FormParser]` si el ViewSet recibe archivos
4. **Ownership**: `get_queryset()` filtra por usuario si no es admin; mantener `queryset = Model.objects.none()` como class attr
5. **Celery + tenant**: toda task que toque TENANT_APPS va envuelta en `tenant_context(tenant)`

## Módulos existentes (17 apps)

`tenants` · `accounts` · `proveedores` · `empleados` · `recintos` · `documentos` · `eventos` · `citas` · `acceso` · `gafetes` · `sanciones` · `dispositivos` · `mensajeria` · `cumplimiento` · `ocr` · `config` · `soporte`

## Integraciones

| Servicio | Uso | Config |
|---|---|---|
| UltraMsg | WhatsApp messaging | `ULTRAMSG_*` en .env |
| AWS Textract | OCR de INE | `AWS_*` en .env |
| Stripe | Billing (pendiente) | `STRIPE_*` en .env |
| Sentry | Error tracking | `SENTRY_DSN` en .env |
| Mailpit | Email dev | `EMAIL_*` en .env |
