# Changelog — Xenty Acceso

Formato basado en [Keep a Changelog](https://keepachangelog.com/). Solo agregar, nunca eliminar.

---

## [Sin release] — 2026-07-02

### Agregado
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
