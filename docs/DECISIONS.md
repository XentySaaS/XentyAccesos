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
