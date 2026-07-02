# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).

## Resumen ejecutivo

Xenty Acceso es un SaaS multitenant de control de accesos a recintos, reconstruido desde Laravel a Django+React. Las fases F0–F7 tienen backend completo (auth, CRUD, eventos, citas, acceso, dispositivos edge, mensajería, cumplimiento). Esta sesión se concentró en **completar y corregir el módulo de escáner QR** (F5) — que ya existía pero le faltaban piezas críticas — y en dos bugs de infraestructura que bloqueaban funcionalidad ya construida (fotos de empleados, QR de gafetes ilegible).

## Estado por módulo (verificado leyendo código — ver `docs/STATUS.md` para detalle completo)

| Módulo | Estado | Notas |
|---|---|---|
| tenants + auth (F0) | ✔ | JWT dual (acceso/proveedores), Argon2id, MFA TOTP |
| accounts (F1) | ✔ | CRUD usuarios, roles, PermisoUsuario granular |
| proveedores (F1) | ✔ | Login, onboarding, CuentaProveedor |
| empleados (F1) | ✔ | CRUD, import Excel, foto (fix de `/media/` esta sesión) |
| recintos (F1) | ✔ | Topología completa |
| documentos (F2) | ✔ | TipoDocumento, verificación |
| eventos (F3) | ✔ | CRUD + gafete QR + ayuda contextual (ⓘ) esta sesión |
| citas (F4) | ✔ | CRUD + gafete adaptativo + email |
| **acceso / escáner (F5)** | ✔ | **Completado esta sesión** — ver detalle abajo |
| sanciones (F5) | ✔ | CRUD |
| gafetes | ✔ | Fernet QR + **fix de legibilidad del QR esta sesión** (ver Issues) |
| dispositivos (F6) | ✔ | EdgeHMACAuthentication + nonce anti-replay (Redis) |
| mensajeria (F7) | ✔ | Backend + retry Celery + UI |
| cumplimiento (F7) | ⚠ | Backend completo; **sin UI** |
| config/reportes (F8) | ⚠ | Sin auditar cobertura del ETL |
| soporte | ⚠ | Mesa de Ayuda stub |
| frontend-acceso | ✔ | Todas las pantallas operativas excepto cumplimiento |
| frontend-proveedores | ✔ | Onboarding, empleados, docs, eventos |
| frontend-admin | ⚠ | Solo Login + lista Tenants |
| tests | ⚠ | Sigue faltando la suite `-k aislamiento` obligatoria (bloqueante, ver Próximos pasos) |

## Última sesión (2026-07-02, continuación)

### 1. Fix `/media/` — fotos de empleados no se servían
Nginx no tenía `location /media/` (caía en el SPA) y Django no tenía `static()` en dev.
- `backend/config/urls.py` — `static(MEDIA_URL, document_root=MEDIA_ROOT)` si `DEBUG`.
- `nginx/nginx.conf` — `location /media/ { proxy_pass http://backend:8000; }` en el server block del tenant.
- Verificado con `curl` contra la URL real (`/media/<schema>/...` — el schema del tenant va en la ruta vía `TenantFileSystemStorage`).

### 2. Módulo de escáner QR (eventos + citas + parking) — completado
El backend (`apps.acceso.services.procesar_escaneo`) y el frontend (`Escaner.tsx`) ya existían pero estaban incompletos. Se investigó el comportamiento del sistema Laravel legado (`proyecto_original/`) solo como referencia de negocio, sin portar código.

**Backend** (`backend/apps/acceso/services.py`, `views.py`):
- **Identidad en la respuesta del escaneo**: `EscanearView` ahora devuelve `nombre`/`empresa`/`foto_url` del portador del QR (antes solo `permitido`/`motivo`) — el guardia puede cotejar visualmente. Función `_identidad()` en `views.py` resuelve desde `RegistroAcceso.empleado`/`.asistente`.
- **Toggle automático entrada/salida**: re-escanear el mismo QR con una entrada abierta hoy registra la salida en vez de una nueva entrada (`_salida_abierta()`, aplica a evento/cita/parking). ⚠️ Bug corregido durante el desarrollo: el filtro inicial también capturaba registros **denegados** (ambos tienen `hora_salida IS NULL`) — se agregó `tipo_acceso=ENTRADA` al filtro.
- **Validación de cita reforzada**: `_escaneo_cita` antes solo revisaba `Cita.estado != CANCELADA`. Ahora también valida `AsistenteCita.estado != CANCELADO` y `Cita.fecha == hoy` (vigencia por día, igual patrón que eventos).
- **Vigencia en parking**: `_escaneo_parking` ahora valida `vigencia_inicio/fin` del evento padre (antes no validaba nada más que la existencia del cajón).
- **Rechazo manual del guardia**: nueva acción `POST /api/acceso/registros/{id}/rechazar/` en `RegistroAccesoViewSet` — convierte una entrada recién concedida en denegada con motivo obligatorio (caso: "la foto no coincide con la persona"). Solo aplica a una entrada abierta sin salida; 409 si ya se resolvió, 400 si falta motivo.
- Todo verificado con pruebas directas contra la BD real del tenant `rayados` (toggle, denegación, rechazo, casos 400/409) — no solo lectura de código.

**Frontend** (`frontend-acceso/src/pages/Escaner.tsx`):
- Botón "¿No es la persona? Rechazar acceso" en la pantalla PERMITIDO, con formulario de motivo.
- **Escaneo por cámara** (nuevo): se instaló `html5-qrcode`; toggle "Usar cámara" / "Usar lector físico", **cámara activada por defecto** con preferencia guardada en `localStorage` (`xenty_escaner_camara`).
- **Confirmación manual en vez de auto-avance**: se quitó el `setTimeout` que regresaba solo al escáner tras 2.5s — ahora el guardia debe tocar "Continuar" (igual que ya hacía DENEGADO), dando tiempo real de cotejar foto/documentos.
- **Integrado al layout del panel**: antes era `fixed inset-0` (tapaba sidebar/topbar); ahora es contenido normal dentro del `<Outlet/>`, visualmente consistente con el resto de la app.
- ⚠️ Bug corregido: `html5-qrcode` lanza **excepciones síncronas** (no promesas rechazadas) al llamar `.stop()`/`.clear()` sobre un scanner que nunca llegó a `SCANNING` (p. ej. permiso de cámara denegado) — causaba un crash total de la SPA ("Unexpected Application Error"). Se corrigió rastreando explícitamente si `.start()` resolvió antes de intentar detener, con `try/catch` real además del `.catch()` de promesa.

### 3. Fix crítico: QR de gafetes ilegible por cámara
Reportado por el usuario ("los gafetes están pixeleados"). Causa raíz confirmada empíricamente con OpenCV: un token Fernet cifrado necesita ~65-70 módulos de QR (el overhead de cifrado domina el tamaño, casi sin importar el contenido), pero `apps/gafetes/services.py` generaba el QR a resolución nativa y lo reducía con `Image.NEAREST` a solo 92-108px — **~1.2px por módulo, matemáticamente imposible de escanear**.
- Nueva función `_qr_imagen()` que mide los módulos necesarios primero y genera el QR directo al tamaño final (sin reescalado con pérdida).
- `QR_BOX` agrandado en ambos diseños de gafete (evento/cita: 108→300px; parking: 100→300px, movido a su propia sección en vez de compartir fila con el número de cajón) para lograr ~4px/módulo.
- Verificado end-to-end: generación real + decodificación con OpenCV, ambos gafetes decodifican correctamente ahora.
- ⚠️ **Los gafetes ya emitidos/enviados antes de este fix siguen siendo ilegibles** — hay que regenerarlos/reenviarlos si se necesitan. No se hizo automáticamente (se le preguntó al usuario, no respondió aún).

### 4. Ayuda contextual (ícono ⓘ) en el módulo de Eventos
`docs/AYUDA_CONTEXTUAL.md` (nuevo, agregado por el usuario) especifica la convención — aunque el archivo referencia rutas y dominio (nómina/fiscal) de otro producto de la suite Xenty; se adaptó a la estructura real de este repo.
- Componente nuevo: `frontend-acceso/src/components/Ayuda.tsx` (ícono `Info` de lucide + `Popover` de `@radix-ui/react-popover`, nueva dependencia instalada — el stack de `CLAUDE.md` ya lo exige pero no estaba en uso en esta SPA).
- Aplicado a **todos** los campos de captura de `Eventos.tsx`: modal crear/editar evento y modal de invitaciones a proveedores. Se restructuraron los `<label>` que envolvían el input (patrón previo) a `<label htmlFor>` + `<Ayuda>` como hermanos + `id` explícito, para no romper la asociación label↔input ni el patrón de accesibilidad.
- Campos de solo lectura (disabled) se dejaron sin ⓘ (no son captura).

## Archivos modificados (esta sesión)

- `backend/config/urls.py` — `static()` de media en dev
- `nginx/nginx.conf` — `location /media/`
- `backend/apps/acceso/services.py` — toggle entrada/salida, vigencia cita/parking, identidad
- `backend/apps/acceso/views.py` — `_identidad()`, acción `rechazar`
- `backend/apps/gafetes/services.py` — `_qr_imagen()`, QR_BOX agrandado en ambos diseños
- `docs/SAR_FUNCIONALIDADES.md` — §9 actualizado para reflejar el comportamiento real
- `frontend-acceso/src/pages/Escaner.tsx` — rechazo, cámara, confirmación manual, layout integrado
- `frontend-acceso/src/pages/Eventos.tsx` — Ayuda contextual en todos los campos
- `frontend-acceso/src/components/Ayuda.tsx` — nuevo componente
- `frontend-acceso/package.json` — `html5-qrcode`, `@radix-ui/react-popover`

## Contexto no obvio

1. **Fernet + QR pequeño = ilegible**: cualquier gafete/pase nuevo que se diseñe con QR debe reservar **mínimo ~280-300px** para el recuadro del QR (un token Fernet ronda 65-70 módulos). Usar `apps/gafetes/services._qr_imagen()`, nunca `qrcode.make(token).resize(...)` directo.
2. **html5-qrcode lanza excepciones síncronas**, no solo promesas rechazadas — `.stop()`/`.clear()`/`.pause()`/`.resume()` todas pueden `throw` si el estado no es el esperado. Cualquier código nuevo que las llame necesita `try/catch` real, no solo `.catch()`.
3. **DRF Router + queryset**: ViewSets con `get_queryset()` necesitan `queryset = Model.objects.none()` como atributo de clase.
4. **Backend --noreload**: cada cambio `.py` requiere `docker compose restart backend`.
5. **Migraciones**: siempre `migrate_schemas --shared` / `--tenant`. Nunca `migrate` a secas.
6. **Acceso dev**: vía Nginx `tenant.localhost:8080`, NO puertos Vite directos.
7. **`docs/AYUDA_CONTEXTUAL.md` tiene rutas de otro producto** (`frontend/src/...`, dominio nómina/fiscal) — al usarlo de referencia para otros módulos, adaptar rutas (`frontend-acceso/src/...`) y contenido (dominio de accesos, no fiscal).

## Issues abiertos

1. **Bug preexistente en Eventos.tsx** (no corregido, fuera de alcance de la tarea que lo reveló): "Fecha del evento" y "Vigencia del acceso desde" están enlazados al mismo campo de estado (`form.vigencia_inicio`) — son visualmente dos inputs pero uno solo en la práctica.
2. **Gafetes ya emitidos antes del fix de QR siguen ilegibles** — pendiente decidir si se regeneran/reenvían masivamente o se dejan para que se regeneren naturalmente.
3. **"Advertencia" (nota) en Escaner.tsx nunca se activa**: el backend no setea `data.nota` en ningún caso, por lo que ese estado del veredicto (ámbar, "Permitir el paso") queda muerto salvo que se implemente un caso de negocio que lo dispare.

## Próximos pasos

1. Tests pytest (suite `-k aislamiento` obligatoria — sigue bloqueando confianza en el resto, no se tocó esta sesión).
2. Pantalla frontend de cumplimiento SAT 69-B (backend ya existe).
3. Auditar cobertura real del ETL F8 contra `docs/MIGRACION_DATOS_SAR.md`.
4. Decidir sobre gafetes ya emitidos (regenerar o no).
5. Si se replica el patrón de `Ayuda` contextual en otros módulos (Citas, Empleados, Proveedores), reusar el componente ya creado.

## Verificar backend

```bash
docker compose ps backend  # debe estar Up
docker compose logs --tail=5 backend  # "Starting development server"
```
