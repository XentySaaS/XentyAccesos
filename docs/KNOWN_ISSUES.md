# Issues Conocidos — Xenty Acceso

---

## ISSUE-001: ValueError en AuditViewSetMixin con CuentaProveedor

**Estado:** Resuelto (2026-07-02)
**Módulo:** config/services
**Síntoma:** `ValueError: Cannot assign "CuentaProveedor": "HistorialCambio.usuario" must be a "Usuario" instance` al hacer PATCH/POST/DELETE desde panel de proveedores.
**Causa raíz:** `HistorialCambio.usuario` es FK a `accounts.Usuario`. `AuditViewSetMixin` pasaba `request.user` directamente, que puede ser `CuentaProveedor`.
**Fix aplicado:** isinstance check en `registrar()` — si no es `Usuario`, pasa `usuario=None`.
**Archivo:** `backend/apps/config/services.py`

---

## ISSUE-002: CitaViewSet crash en startup (basename)

**Estado:** Resuelto (2026-07-02, commit `4be3b6d`)
**Módulo:** citas/views
**Síntoma:** `AssertionError: basename argument not specified` al arrancar Django. Container exit code 137.
**Causa raíz:** Se removió class-level `queryset` al agregar `get_queryset()`. DRF router necesita uno u otro para inferir basename al registrar URLs.
**Fix aplicado:** `queryset = Cita.objects.none()` como class attribute.
**Archivo:** `backend/apps/citas/views.py`

---

## ISSUE-003: Foto empleado no se visualiza después de subir

**Estado:** Parcialmente resuelto
**Módulo:** frontend-proveedores/Empleados
**Síntoma:** Al cambiar foto de empleado, no se ve la nueva imagen; mostraba iniciales.
**Causa raíz:** (a) `FotoCirculo` no reseteaba estado de error de `<img>` al cambiar `src`. (b) `subirFoto()` tragaba errores silenciosamente. (c) ValueError de ISSUE-001 impedía el PATCH.
**Fix aplicado:** (a) `useEffect(() => setErr(false), [foto])` (b) Feedback visible de error/éxito (c) Fix de ISSUE-001.
**Pendiente:** Confirmar que funciona end-to-end después de reiniciar backend.
**Archivo:** `frontend-proveedores/src/pages/Empleados.tsx`

---

## ISSUE-004: Nginx no sirve /media/ en dev

**Estado:** Abierto
**Módulo:** infra/nginx
**Síntoma:** Fotos subidas podrían no cargar si la URL generada por DRF apunta al puerto interno (8000) y no al de Nginx (8080).
**Causa raíz:** Pendiente de verificar — posible falta de `proxy_pass` para `/media/` en `nginx.conf` o headers `X-Forwarded-*` incorrectos.
**Workaround:** Acceder directamente a `localhost:8002/media/...` (puerto mapeado del backend).
**Fix aplicado:** Pendiente.

---

## ISSUE-005: Gafete de cita mostraba placeholder de foto roto

**Estado:** Resuelto (2026-07-02)
**Módulo:** gafetes/services
**Síntoma:** Rectángulo casi invisible (white alpha 10) con silueta fantasmal (alpha 51) en la sección de foto del gafete.
**Causa raíz:** El placeholder se diseñó para cuando SÍ hay foto (overlay sutil); sin foto, era casi invisible sobre fondo oscuro.
**Fix aplicado:** Layout adaptativo: sin `foto_bytes` se elimina el recuadro, zona usa ancho completo, fuente más grande, altura reducida.
**Archivo:** `backend/apps/gafetes/services.py`
