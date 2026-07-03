# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).

## Resumen ejecutivo

Xenty Acceso es un SaaS multitenant de control de accesos a recintos, reconstruido de Laravel a Django+React. Las fases F0–F7 tienen backend completo. Esta tanda de sesiones se dedicó a **cerrar paridad con el sistema Filament original** (escáner, gafetes, sanciones, bitácora, calendario, reportes, cumplimiento 69-B, dashboard) y a mejoras transversales (ayuda contextual, idempotencia, notificaciones WhatsApp). El **cumplimiento SAT 69-B quedó funcional y con arquitectura de padrón global**.

## Estado por módulo (verificado leyendo código)

| Módulo | Estado | Notas |
|---|---|---|
| tenants + auth (F0) | ✔ | JWT dual, Argon2id, MFA TOTP |
| accounts (F1) | ✔ | CRUD, roles, PermisoUsuario granular |
| proveedores (F1) | ✔ | Onboarding + validación 69-B al alta (usa padrón global) |
| empleados (F1) | ✔ | CRUD, import Excel, foto (fix `/media/`) |
| recintos (F1) | ✔ | Topología + ayuda contextual |
| documentos (F2) | ✔ | Verificación |
| eventos (F3) | ✔ | CRUD + gafete QR + ayuda contextual |
| citas (F4) | ✔ | CRUD + gafete + email/WhatsApp |
| acceso/escáner (F5) | ✔ | Escáner cámara+HID, toggle entrada/salida, rechazo del guardia, columna Fecha, export Excel |
| sanciones (F5) | ✔ | severidad/penalidad admin-only, flujo evento→empleado, escaneo QR, botón "Asignar sanción" |
| gafetes | ✔ | QR Fernet legible (fix de densidad) |
| dispositivos (F6) | ✔ | Edge HMAC + nonce |
| mensajeria (F7) | ✔ | Campañas WhatsApp + **adjunto de archivo** + segmentación |
| **cumplimiento 69-B (F7)** | ✔ | **Funcional + padrón GLOBAL + UI + auto-actualización** — ver abajo |
| bitácora (eventos) | ✔ | Dossier de solo lectura por evento (nuevo módulo sidebar) |
| calendario | ✔ | Módulo sidebar, vista de mes, modal de detalle evento/cita |
| dashboard | ✔ | KPIs + accesos/hora reales + eventos en curso + widget 69-B |
| config/reportes (F8) | ⚠ | Dashboard/calendario/export OK; ETL sin auditar |
| tests | ✔/⚠ | **Suite `-k aislamiento` HECHA** (`tests/test_aislamiento_tenants.py`, 8 verdes). Falta ampliar cobertura a otros módulos |
| frontend-admin | ✔ | Login (**con paso MFA**) + **dashboard** + Tenants + **detalle de tenant** (billing/checkout + **créditos**) + **Planes CRUD** + **Seguridad/MFA TOTP**. Control plane funcionalmente completo |

## Trabajo de esta tanda (commits `ed3da00`..`d7718f7`)

Todo lo de abajo está commiteado y pusheado a `origin/main`.

### Escáner de acceso
- Cámara (html5-qrcode) + lector HID + manual; **confirmación manual** (sin auto-avance) para cotejar foto/documentos; **rechazo manual del guardia** (`POST /api/acceso/registros/{id}/rechazar/`); toggle entrada/salida al re-escanear; integrado al layout del panel.
- Fix crash: html5-qrcode lanza **excepciones síncronas** en stop/clear si nunca arrancó (permiso denegado) → manejado.
- Fix responsive: CSS fuerza el `<video>` dentro del recuadro (`object-fit: cover`).

### Gafetes
- Fix crítico de **QR ilegible**: un token Fernet necesita ~65-70 módulos; se generaba grande y se reducía con NEAREST a <1.5px/módulo. Nueva `_qr_imagen()` genera al tamaño final; recuadro agrandado a ~300px. Verificado con OpenCV.

### Sanciones
- severidad/penalidad **solo admin** (serializer las ignora para no-admin; frontend las oculta).
- Flujo **evento→empleado**: primero evento activo, luego búsqueda de empleado **acotada a asistentes de ese evento** (autocomplete, no select). Escaneo QR del gafete resuelve empleado+evento.
- **Botón "Asignar/Editar sanción"** por fila (admin) para definir penalidad de una amonestación pendiente (PATCH).

### Bitácora, Calendario, Reportes
- **Bitácora** (`GET /api/eventos/{id}/bitacora/`): dossier por evento con proveedores + staff; página sidebar.
- **Calendario**: módulo sidebar, vista de mes hecha a mano (sin librerías), eventos azul/citas verde, **modal de detalle** al clic. `CalendarioView` enriquecido y por-rol.
- **Reporte de accesos**: `ExportarAccesosView` con columnas legibles + filtros; botón "Exportar Excel" en Accesos (admin). Columna **Fecha** en la bitácora. (El `ReportChangeHistory` del origen era un stub; ya lo supera `Historial`.)

### Dashboard
- Accesos por hora **reales** (no mock) + widget **"Eventos en curso"** (invitados/ingresados/%). Se eliminaron los avisos falsos hardcodeados.
- Widget de **cumplimiento 69-B siempre visible** (admin): verde limpio / azul actualizando / rojo con lista de marcados.

### Cumplimiento SAT 69-B — el grande
- **Importador funcional**: parsea el CSV real del SAT (2 filas de título, encabezado dinámico, acentos, Latin-1). Antes traía 154 filas por dos bugs: (a) `nombre` era CharField(255) pero la razón social del SAT llega a ~587 chars → error abortaba el loop; ahora `TextField`. (b) `update_or_create` por fila era lentísimo → **bulk upsert** (`ON CONFLICT`), ~14k filas en ~16s. Estatus normalizado sin acentos/mayúsculas.
- **Padrón GLOBAL** (petición del usuario): `SatEfo` se movió al app compartido nuevo **`apps.efos` (SHARED_APPS)** → una sola copia en schema público, no duplicada por tenant. La **validación es por tenant** (lee el padrón compartido vía `public` en el search_path, escribe `ResultadoLista69b` en su schema).
- **Auto-actualización sin acción del admin**: Celery beat `sincronizar_efos_todos` (día 1 de cada mes 03:00) importa una vez y revalida cada tenant. Auto-reparación diferida: `ResumenView` con padrón vacío encola `importar_efos_task`.
- UI: página **Cumplimiento** (sidebar, admin) + alerta en dashboard. Endpoints `resumen`, `revalidar`, `validar/{id}`. Comando `manage.py importar_efos` (archivo/URL, revalida).

### Transversales
- **Ayuda contextual (ⓘ)**: componente `frontend-acceso/src/components/Ayuda.tsx` (Radix Popover) en Eventos, Citas, Sanciones, Usuarios, Recintos, Proveedores, Catálogos, Mensajería. Convención registrada en CLAUDE.md §8 y `docs/AYUDA_CONTEXTUAL.md`.
- **Idempotencia** (anti doble-submit): cliente axios de los 3 SPAs deduplica POST/PUT/PATCH en vuelo + `Idempotency-Key`; middleware `config.middleware.idempotency.Idempotency` repite respuesta cacheada por tenant. Automático.
- **Notificaciones WhatsApp**: helper `notificar_whatsapp` en `apps.mensajeria.services`; toda notificación (citas, proveedores, eventos) manda WhatsApp si hay teléfono.

## Contexto no obvio (IMPORTANTE)

1. **Nginx cachea la IP del backend**: al reiniciar/recrear el contenedor `backend`, Nginx sigue apuntando a la IP vieja → **502 en toda `/api/`** (el SPA carga pero no deja acceder). **Solución: `docker compose restart nginx`** después de reiniciar el backend. (Pendiente opcional: `resolver` de Docker en nginx.conf para que re-resuelva por request.)
2. **Padrón 69-B es GLOBAL** (schema público, `apps.efos`). No lo vuelvas a poner por tenant. Se lee desde cualquier tenant vía `public` en el search_path (`rayados, public`). La importación corre en contexto público (sin tenant); la validación en `tenant_context`.
3. **QR/gafetes**: cualquier diseño nuevo con QR debe reservar ~300px para el recuadro (token Fernet ~70 módulos). Usar `apps.gafetes.services._qr_imagen()`, nunca `qrcode.make().resize()`.
4. **html5-qrcode lanza excepciones síncronas** (no promesas) en stop/clear/pause/resume — envolver en try/catch real.
5. **Descarga del SAT**: `SAT_EFOS_CSV_URL` default = CSV público del SAT; requiere salida a internet en prod. En dev el sandbox sí tuvo acceso (importó 14,055).
6. Migraciones: `migrate_schemas --shared` (apps compartidos, incl. `apps.efos`) y `--tenant`. Nunca `migrate` a secas.
7. Backend `--noreload`: cada cambio `.py` requiere `docker compose restart backend` (y luego `restart nginx`, ver #1).
8. **Gracia manual (`Tenant.gracia_hasta`)**: acceso concedido a mano cuando el cliente paga por fuera. Mientras esté vigente, el enforcement exime del bloqueo por **trial vencido** y por **suspensión** (no por cancelado, ni del modo solo-lectura). Se otorga desde el detalle del tenant en frontend-admin. Es acotada en el tiempo (expira sola).

## Issues abiertos

1. ✔ ~~**Suite de tests de aislamiento** (`pytest -k aislamiento`)~~ **RESUELTO (2026-07-02)**:
   `tests/test_aislamiento_tenants.py` (8 tests verdes) + `tests/conftest.py` (fixture `dos_tenants`).
   Incluye la verificación de que el padrón 69-B global no filtra entre tenants. **Para correrla**: la
   imagen backend no trae dev-tools; primero `docker compose exec backend pip install -r
   requirements-dev.txt`, luego `docker compose exec backend python -m pytest -k aislamiento`
   (~2.5 min: cada schema de tenant corre todas las migraciones). Pendiente menor: ampliar cobertura
   de aislamiento a más módulos y considerar añadir dev-deps a la imagen de forma reproducible.
2. **Mensajería adjunto**: el archivo se sube/guarda, pero UltraMsg lo envía por **URL pública** — requiere configurar `MEDIA_PUBLIC_BASE_URL` en prod; en dev degrada a solo texto.
3. **Bug preexistente Eventos.tsx**: "Fecha del evento" y "Vigencia del acceso desde" comparten el mismo campo (`form.vigencia_inicio`).
4. **Estado "advertencia" del escáner** nunca se dispara (el backend no setea `data.nota`).
5. **Proveedor local de WhatsApp con failover** (petición grande previa): quedó pendiente por decisión de transporte (Python puro vs worker Node/Baileys). Ver esa conversación.

## Próximos pasos sugeridos

1. Ampliar la suite de aislamiento a más módulos (empleados/eventos/citas/acceso) y hacer las
   dev-deps reproducibles en la imagen (o un servicio `test` en compose).
2. Configurar `MEDIA_PUBLIC_BASE_URL` en prod para adjuntos de WhatsApp.
3. Auditar ETL F8 vs `docs/MIGRACION_DATOS_SAR.md`.
4. Completar frontend-admin (control plane).

## Verificar servicios

```bash
docker compose ps                    # todos Up
docker compose restart backend nginx # tras cambios .py (nginx por el punto #1)
curl -s -o /dev/null -w "%{http_code}" http://rayados.localhost:8080/api/auth/me/   # 401 = API viva
```
