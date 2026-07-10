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

---

## ISSUE-006: Mesa de Ayuda (Nivel B) es cliente-only — servicio externo pendiente

**Estado:** Abierto (ocultado temporalmente en UI, 2026-07-10)
**Módulo:** apps.soporte + frontend-acceso/Soporte
**Síntoma:** El panel de Soporte permite configurar una "Mesa de Ayuda" con `base_url` + `api_key` y ofrece "Probar conexión" / "Enviar diagnóstico", pero **no existe ningún servicio de Mesa real**. La URL de ejemplo `https://mesa.xenty.mx` (placeholder en `Soporte.tsx`) no resuelve a nada; no hay servicio en `docker-compose.yml` ni variables en `.env`.
**Causa raíz:** `apps.soporte` es solo el **cliente** de una Mesa de Ayuda externa (Nivel B). El servidor que debe exponer `GET /health` y `POST /diagnosticos` con auth `Bearer` es un sistema aparte que aún no se construye/despliega. Sin config, el cliente corre en **sandbox** (no hace red): "Probar conexión" devuelve *"Mesa de Ayuda no configurada"* y "Enviar diagnóstico" no envía nada (`apps/soporte/services.py:es_sandbox`).
**Mitigación aplicada:** Se ocultó el ítem "Soporte" del menú (`frontend-acceso/src/components/Layout.tsx`, `NAV_ITEMS` comentado). La ruta `/soporte` sigue registrada en el router (accesible por URL directa), y el backend `/api/soporte/*` sigue activo — solo se retiró el acceso visible para no dar a entender que la Mesa ya funciona.
**Pendiente:** (1) Construir/desplegar el servicio real de Mesa de Ayuda (endpoints `/health` y `/diagnosticos`, auth Bearer). (2) Reactivar el ítem del menú (descomentar en `Layout.tsx`). (3) Considerar cambiar el placeholder `mesa.xenty.mx` por la URL real. No confundir con `ConfiguracionConnector` (XCC), que es global y del super-admin.
**Archivos:** `frontend-acceso/src/components/Layout.tsx`, `frontend-acceso/src/pages/Soporte.tsx`, `backend/apps/soporte/`
