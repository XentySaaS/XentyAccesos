# Decisiones Técnicas — Xenty Acceso

> Solo agregar (append-only). Nunca eliminar decisiones antiguas.

---

## DEC-001: Reconstrucción limpia, no paridad 1:1

**Fecha:** 2026-05 (diseño F0)
**Problema:** El sistema origen (Laravel/Filament/MySQL) tiene deuda técnica significativa: typos en tablas, FKs faltantes, AES-ECB con clave en git, controladores monolíticos.
**Alternativas:** (a) Migrar manteniendo estructura (b) Reconstruir sobre stack Xenty
**Decisión:** Reconstrucción completa. Se corrigen nombres, se agregan FKs reales, se reimplementa seguridad.
**Justificación:** Portar deuda haría el sistema inmantenible. El esquema destino corrige errores del origen.
**Impacto:** No se copia código del repo viejo; se usa como referencia de comportamiento.

---

## DEC-002: Dos contextos de autenticación separados

**Fecha:** 2026-05 (diseño F0)
**Problema:** Dos tipos de actores autenticados — staff del recinto vs proveedores externos.
**Alternativas:** (a) Un solo modelo User con flag (b) Dos modelos con JWT separados
**Decisión:** `Usuario` (ctx=acceso) y `CuentaProveedor` (ctx=proveedores) son modelos separados con flujos JWT distintos.
**Justificación:** Aislamiento de seguridad; no mezclar credenciales entre contextos operativos y de autoservicio.
**Impacto:** Todos los ViewSets verifican `ctx` via `ContextoAcceso` o `ContextoProveedores`.
**Archivos:** `backend/common/permissions.py`, `backend/apps/accounts/`, `backend/apps/proveedores/`

---

## DEC-003: Fernet para QR en lugar de AES-ECB

**Fecha:** 2026-05 (diseño F0)
**Problema:** Sistema origen usaba AES-128-ECB con clave fija en git para tokens QR.
**Alternativas:** (a) AES-GCM manual (b) Fernet (AES-128-CBC + HMAC) (c) JWT firmado
**Decisión:** Fernet con `jti` único + `exp` + `tenant` claim.
**Justificación:** Fernet provee cifrado autenticado; jti previene replay; tenant previene falsificación cross-tenant. Librería estándar de `cryptography`.
**Impacto:** `SECRET_KEY_FERNET` separada de `SECRET_KEY`. Token QR contiene payload firmado y cifrado.
**Archivos:** `backend/apps/gafetes/services.py`, `backend/common/crypto.py`

---

## DEC-004: HistorialCambio.usuario acepta None para actores no-Usuario

**Fecha:** 2026-07-02
**Problema:** `AuditViewSetMixin.perform_update()` crasheaba con `ValueError: must be a Usuario instance` cuando `request.user` era `CuentaProveedor`.
**Alternativas:** (a) GenericForeignKey para usuario (b) isinstance check con fallback None (c) Segundo campo FK
**Decisión:** En `registrar()`, isinstance check — si no es `Usuario`, pasa `usuario=None`.
**Justificación:** FK es nullable; más simple que GenericFK; el audit trail se preserva en `descripcion` aunque no tenga FK de usuario.
**Impacto:** Cualquier ViewSet con `AuditViewSetMixin` es seguro para ambos contextos de autenticación.
**Archivos:** `backend/apps/config/services.py`

---

## DEC-005: queryset = Model.objects.none() en ViewSets con get_queryset()

**Fecha:** 2026-07-02
**Problema:** DRF `DefaultRouter` requiere class-level `queryset` O `basename` explícito para inferir nombres de URL. `CitaViewSet` solo tenía `get_queryset()` → crash en startup.
**Alternativas:** (a) `basename="citas"` en `router.register()` (b) `queryset = Cita.objects.none()` como class attr
**Decisión:** `queryset = Cita.objects.none()` — satisface al router sin afectar runtime (get_queryset lo sobreescribe).
**Justificación:** Patrón estándar DRF. El router inspecciona la clase al importar, no al recibir requests.
**Impacto:** Aplica a todo ViewSet que use `get_queryset()` sin class-level queryset.
**Archivos:** `backend/apps/citas/views.py`

---

## DEC-006: PermisoUsuario — permisos granulares para rol "usuario"

**Fecha:** 2026-07-02
**Problema:** El rol "usuario" no tiene permisos inherentes; los admins necesitan asignar acceso por módulo (ver/crear/editar/eliminar).
**Alternativas:** (a) Expandir RequiereRol con sub-roles (b) Modelo de permisos granulares por módulo
**Decisión:** Modelo `PermisoUsuario` (FK usuario, modulo TextChoices ×8, 4 BooleanFields) + `RequierePermisoPersonalizado(modulo)` + action GET/PUT en `UsuarioViewSet`.
**Justificación:** Más flexible que roles fijos; un admin puede dar acceso a "eventos:ver" sin dar "eventos:eliminar".
**Impacto:** Todos los ViewSets de negocio incluyen `RequierePermisoPersonalizado` en su `permission_classes`.
**Archivos:** `backend/apps/accounts/models.py`, `backend/common/permissions.py`, `backend/apps/accounts/views.py`

---

## DEC-007: Gafete sin foto — layout adaptativo

**Fecha:** 2026-07-02
**Problema:** Los asistentes de citas generalmente no tienen foto; el placeholder (rectángulo casi invisible + silueta fantasmal) se veía roto en el gafete.
**Alternativas:** (a) Mejorar el placeholder (b) Eliminar sección de foto cuando no hay imagen
**Decisión:** Cuando `foto_bytes=None`, se elimina el recuadro de foto; la zona usa ancho completo (304px), fuente Bebas más grande (58px vs 44px), y PZ_H baja de 164 a 114px.
**Justificación:** El gafete de cita es funcional (QR + nombre + fechas); forzar un placeholder vacío degradaba el diseño.
**Impacto:** `componer_gafete()` tiene dos layouts: con foto (columna estrecha para zona) y sin foto (zona full-width).
**Archivos:** `backend/apps/gafetes/services.py`, `backend/apps/citas/services.py`

---

## DEC-008: El Connector (XCC) se despliega en el mismo CD, como servicio opcional y no-afectante

**Fecha:** 2026-07-13
**Problema:** El XCC vive en un repo separado (`ElevationStudioMX/XentyC`) y podría desplegarse por su cuenta. ¿Pipeline/CD separado o unificado con el principal?
**Alternativas:** (a) CI/CD totalmente separado del XCC (b) Deploy unificado en el mismo CD, pero con el XCC como servicio opcional
**Decisión:** El XCC se incluye en el **mismo CD** que el principal, pero como servicio **opt-in** (p. ej. `profiles: ["connector"]` en el compose de deploy / paso opcional del pipeline). En producción puede **no levantarse**, y su ausencia o caída **no debe afectar** el funcionamiento del principal.
**Justificación:** Un solo pipeline simplifica la operación (un release, un host), pero el XCC es un respaldo no-oficial (Baileys) que puede fallar/banearse; acoplarlo como obligatorio arriesgaría al principal. La no-afectación **ya está garantizada por arquitectura**: master switch global (`ConfiguracionConnector.habilitado`) + Router con failover a UltraMsg/Sandbox + breaker. El XCC nunca es dependencia dura.
**Impacto:** Cuando exista el CD (falta host), el XCC entra como servicio opcional; su imagen se construye del repo del XCC. Con el master switch OFF o el contenedor apagado, el principal opera igual. Artefactos de deploy del XCC: `xenty-connector/DEPLOY.md`, `docker-compose.prod.yml`, `nginx.xcc.conf.example`.
**Archivos:** `docs/ARQUITECTURA_CONNECTOR.md` §14, `xenty-connector/DEPLOY.md`

---

## DEC-009: El panel de proveedores vive en subdominios por tenant; se rechaza el host único

**Fecha:** 2026-07-21
**Problema:** Tras separar proveedores a su propio espacio de dominios (hub `proveedores.<dominio>` + panel `<slug>.proveedores.<dominio>`), se propuso que TODO viviera en un solo host (`proveedores.<dominio>/login`, `/dashboard`) con un select para cambiar de tenant dentro del panel.
**Alternativas:** (a) Host único con tenant resuelto por claim del JWT / header `X-Tenant` (b) Mantener subdominios por tenant y dar el mismo UX con un selector de espacios que navegue entre hosts
**Decisión:** Se mantienen los **subdominios por tenant** (opción b). El host único queda rechazado.
**Justificación:** El host único rompe la invariante estructural host→schema: la validación del claim `tenant` se vuelve circular (el schema se elegiría desde el propio token), los endpoints sin sesión (login, reset) pasarían a confiar en un tenant elegido por el cliente, el enforcement por middleware tendría que reordenarse, y —lo que ningún código arregla— todos los tokens de todos los espacios del proveedor vivirían en UN solo origen del navegador (un XSS expondría todas las sesiones a la vez; hoy cada tenant es un origen aislado). Contradice CLAUDE.md §4 («aislamiento por DB, no por disciplina de código»). El beneficio era cosmético (la URL); el proveedor entra por el hub, por links de correo o por el selector, nunca tecleando el dominio. XentyFiscal usa el mismo patrón (selector central → subdominio del workspace).
**Impacto:** La experiencia se unifica por UI, no por dominio: hub con código de verificación por dispositivo + onboarding, login del panel con marca del recinto (`GET /api/publico/marca/`) y link «← Elegir otro espacio». Pendiente opcional (no confirmado): selector de espacios en el header del panel que navegue entre hosts.
**Archivos:** `backend/common/jwt.py`, `backend/apps/tenants/hub_proveedores_api.py`, `backend/common/panel_proveedores.py`, `nginx/nginx.conf`, `handoffs/HANDOFF_LATEST.md` (continuaciones 33-37)
