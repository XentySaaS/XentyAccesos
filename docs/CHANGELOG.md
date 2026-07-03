# Changelog — Xenty Acceso

Formato basado en [Keep a Changelog](https://keepachangelog.com/). Solo agregar, nunca eliminar.

---

## [Sin release] — 2026-07-02

### Agregado
- **Periodo de gracia manual por tenant** (pago externo sin activación automática): campo
  `Tenant.gracia_hasta` (migración `tenants.0002`, SHARED). Mientras `ahora < gracia_hasta` el
  enforcement **no bloquea** por trial vencido ni por suspensión (sí sigue bloqueando cancelado y el
  modo solo-lectura de escritura). Acción `otorgar-gracia` en `TenantAdminViewSet`
  (`/api/admin/tenants/{id}/otorgar-gracia/`, `dias` 1–365; `dias=0` revoca) + sección "Periodo de
  gracia" en `TenantDetalle.tsx` (otorgar/extender/quitar, muestra días restantes y fecha de vencimiento).
  Visibilidad: badge "en gracia" en la lista de Tenants y KPI "En gracia" en el dashboard.
- **frontend-admin — asignar plan a un tenant** (sección Plan en `TenantDetalle.tsx`): selector de
  plan + "Asignar". Backend: acción `asignar-plan` en `TenantAdminViewSet`
  (`/api/admin/tenants/{id}/asignar-plan/`) que fija/quita `tenant.plan` (gobierna módulos y checkout
  por defecto; no crea la suscripción Stripe). Antes el plan solo se asignaba al alta o en el checkout.
- **frontend-admin — otorgar créditos a un tenant** (sección en `TenantDetalle.tsx`): acredita o
  ajusta créditos con cantidad + motivo. Backend: acción `creditos` en `TenantAdminViewSet`
  (`/api/admin/tenants/{id}/creditos/`) que llama a `billing.acreditar_creditos` (ledger
  append-only) con referencia `admin:<pk>`. Con esto el control plane queda funcionalmente completo.
- **frontend-admin — gestión de Planes (CRUD)** (`frontend-admin/src/pages/Planes.tsx`, ruta
  `/planes`): alta/edición/baja de planes comerciales (precio, módulos incluidos con checkboxes,
  límites como JSON, stripe_price_id, activo). Backend nuevo: `PlanAdminViewSet` (ModelViewSet) en
  `apps/tenants/admin_api.py`, ruta `/api/admin/planes/`; `destroy` responde 409 si el plan tiene
  suscripciones (FK PROTECT) sugiriendo desactivar. Sin migración (el modelo `Plan` ya existía).
- **frontend-admin — MFA del super-admin** (`frontend-admin/src/pages/Seguridad.tsx`, ruta
  `/seguridad`): enrolar/activar TOTP (muestra clave secreta + URI `otpauth` para la app
  autenticadora) y estado actual. El **login ahora maneja la sesión MFA-pendiente**: si el token
  trae `mfa="pending"` pide el código de 6 dígitos y llama a `/api/admin/mfa/verificar/` antes de
  entrar (`src/lib/jwt.ts` decodifica el claim). Backend: `MeView` (`common/auth_api.py`) ahora
  incluye `mfa_habilitado` (aditivo, aplica a los tres contextos).
- **frontend-admin — dashboard de control-plane** (`frontend-admin/src/pages/Dashboard.tsx`, ruta
  `/dashboard`, ahora landing tras login): KPIs (total tenants, activos, en solo lectura, créditos
  totales), distribución por estado y por plan (barras CSS), y lista de trials por vencer (14 días)
  con enlace al detalle. Solo frontend; consume `/api/admin/tenants/`.
- **frontend-admin — detalle de tenant** (`frontend-admin/src/pages/TenantDetalle.tsx`, ruta
  `/tenants/:id`): ficha con estado/plan/créditos/fin-de-trial, acciones de ciclo de vida
  (suspender/activar/cancelar) y generación de checkout de suscripción Stripe. La lista de Tenants
  ahora enlaza a cada detalle. Consume endpoints ya existentes del control plane; sin cambios de backend.
- **Suite de aislamiento entre tenants** (obligatoria per CLAUDE.md §4): `tests/test_aislamiento_tenants.py`
  (8 tests) + fixture `dos_tenants` en `tests/conftest.py`. Corre con `pytest -k aislamiento`.
  Verifica no-fuga de datos por tenant (Usuario/Proveedor), padrón EFOS 69-B global visible desde
  todos los tenants, resultados 69-B por tenant, cache (Redis) y storage segregados por schema, y
  ausencia estructural de tablas de tenant en el schema `public`.
- Sistema de permisos personalizados para rol "usuario" (PermisoUsuario model, migración 0005, serializer, action GET/PUT en UsuarioViewSet)
- `RequierePermisoPersonalizado(modulo)` permission class integrada en todos los ViewSets de negocio
- Modal de permisos en `frontend-acceso/src/pages/Usuarios.tsx` (8 módulos × 4 acciones)
- `RequiereRol` actualizado en: eventos, citas, acceso, mensajería, sanciones, recintos
- Ownership filtering en CitaViewSet (non-admin solo ve sus citas)
- Layout adaptativo en `componer_gafete()` — sin foto: zona full-width, Bebas 58px, PZ_H=114
- Foto del empleado vinculado se pasa al gafete de citas (si tipo=EMPLEADO)
- Feedback visual de éxito/error al subir foto en Empleados.tsx
- NAV_ITEMS filtrado por rol en Layout.tsx

### Corregido
- **Hardening — `/media` en dev ya no expone archivos privados (REMEDIACION §C5 / ISSUE-004)**: el
  serve de `/media` en dev bloquea los directorios con PII/documentos (`ine`, `repse`, `sua`,
  `documentos`) y solo sirve no-sensibles (fotos). Los privados se descargan por endpoints
  autenticados con policy de pertenencia (`documentos.download`, `proveedores.documento`). En prod
  (`DEBUG=False`) Django no sirve `/media` en absoluto. Verificado: foto→200, INE→404.
- **Hardening — redacción de PII en logs (REMEDIACION §A7)**: se cableó `LOGGING` con
  `common.observability.RedaccionPIIFilter`, que borra RFC/CURP/email de cada mensaje antes de
  emitirlo (el redactor existía pero no estaba conectado; la app usa `logging` estándar, no structlog).
  Verificado: `logger.info("Correo a %s curp %s", email, curp)` → `Correo a [EMAIL] curp [CURP]`.
- **Hardening — rate limiting de login + semántica 429** (REMEDIACION §A4): los tres logins (acceso,
  proveedores, super-admin) ahora tienen rate limit (`10/m` por IP, heredado de `BaseLoginView`);
  antes no tenían ninguno (fuerza bruta). Nuevo `EXCEPTION_HANDLER` (`common/exceptions.py`) convierte
  `Ratelimited` en **429** en vez del 403 genérico, para todos los endpoints con límite
  (login/signup/onboarding/edge/ocr). Verificado en runtime: el 11º intento de login → 429.
- **MFA admin — QR real en lugar de solo el URI**: `EnrolarTOTPView` (`common/mfa_api.py`) ahora
  devuelve `qr` (PNG en base64/data-URI generado en el servidor con `qrcode`, sin exponer el secreto
  a servicios externos) y `Seguridad.tsx` lo renderiza. Antes el texto decía "escanea el URI" pero
  no había código escaneable.
- `CitaViewSet` crash en startup: `queryset = Cita.objects.none()` para basename DRF router (`4be3b6d`)
- `AuditViewSetMixin` ValueError con CuentaProveedor: isinstance check en `registrar()` (`config/services.py`)
- `FotoCirculo` no actualizaba imagen al cambiar foto: `useEffect(() => setErr(false), [foto])`
- `http_method_names` faltaba "put" en UsuarioViewSet — bloqueaba PUT en action permisos (`58b0853`)
- Error catch en modal de permisos no mostraba código HTTP (`dbee974`)
- Silueta del placeholder en gafete casi invisible (alpha 51→90)

---

## [Sin release] — 2026-06-28

### Agregado
- Implementación completa de citas: serializers, buscar-personas, servicios y UI (`89c8c12`)
- Rediseño pase de estacionamiento Premium Dark (`1b7282e`)
- Rediseño gafete Premium Dark con acento dorado + logos + HTML emails (`415957e`)

### Corregido
- Grilla amarilla removida del gafete, logo Xenty real en header (`c72a1d4`)
- `get_permissions()` debe retornar instancias no clases en documentos (`7cb38ec`)

---

## [Sin release] — 2026-06-26

### Agregado
- Upload docs empleados, QR parking descargable y gafete adjunto en notificación (`488a0f8`)
- Frontend-admin: diseño unificado con sidebar oscuro y pantalla Tenants (`ab1c6b1`)
- Frontend-proveedores: SPA completa con onboarding, eventos y asignación progresiva (`79c508c`)
- Frontend-acceso: diseño unificado, pantallas completas y corrección de rutas API (`f8f58d6`)
- Backend: módulo completo eventos, documentos, OCR, proveedores y gafetes (`0afde1a`)

### Corregido
- JWT sesión expirada: 8h/30d + aviso en login + redirect desde interceptor (`f87a1a7`)
- Verificación de documentos, edición de empleados y upload en pantalla de empleados (`cfee34e`)

---

## [Sin release] — 2026-06-24

### Agregado
- Pantallas Mensajería, Verificación docs y fix file-watcher Docker/Windows (`432782d`)
- Pantallas Citas, Sanciones y SPA Proveedores completa (`ce7aafa`)
- Timestamps creado/actualizado en todos los modelos del data plane (`73d2306`)
- Pivotes de áreas autorizadas (evento, cita, evento-proveedor) + migración tenant en arranque (`6d723a3`)
- Super-admin único (singleton) y confirma primer usuario del tenant = administrador (`4939f02`)
- Pantallas Eventos (máquina de estados), Escáner de acceso y Dashboard con KPIs (`eb773f5`)
