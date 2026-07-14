# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual) → `docs/STATUS.md`
> (estado vivo por módulo).
> Actualizado: **2026-07-13**. El anterior (2026-07-10: tests MFA, recuperación de contraseña,
> Mesa de Ayuda oculta, documentos legales) está en `handoffs/history/HANDOFF_2026-07-10.md`.

---

## Resumen ejecutivo

Sesión de **hardening + una feature de operación + documentación**. Cinco commits, todos en
`origin/main`, árbol limpio:

1. **`f5bfd00`** `style` — `ruff format` sobre 5 archivos que rompían CI (`ruff format --check`).
2. **`d206995`** `chore(dev)` — **pre-commit hook** con ruff (format + check --fix) vía Docker, para
   que el formato no vuelva a romper CI.
3. **`9779985`** `fix(mfa)` — **el secreto TOTP ya no se persiste hasta confirmar el enrolamiento**
   (arreglo del bug del QR que "desaparecía"). Ahora vive en cache hasta activar.
4. **`c85110f`** `docs` — seguimiento del **Connector (XCC)** en `docs/STATUS.md` (fases F-C/F-D/F-E +
   decisión pendiente de proveedor de WhatsApp).
5. **`90e031b`** `feat(admin)` — el super-admin puede **reenviar** o **verificar manualmente** el
   correo del administrador de un tenant cuando el doble opt-in no llega.

**Suite completa: 68/68 verdes** (última corrida, ~104 s). `ruff` limpio. Las 4 SPAs compilan.

> **Continuación (misma fecha):** se retomó el **Connector (XCC)** y se **completó F-E (código)**: nonce
> en Redis, repo remoto, métricas Prometheus, webhook de estados, routing sticky / propiedad de sesión,
> `connection_id` por tenant y artefactos de deploy. Solo falta provisionar el XCC en un host. Ver la
> sección "Connector (XCC) — F-E" abajo.
>
> **Continuación 2 (misma fecha):** **estandarización de teléfonos** — el formato canónico pasa a **10
> dígitos sin lada** (Xenty solo opera en México); la lada mexicana se antepone solo al enviar por
> WhatsApp (`common/phone.py`, punto único). Ver la sección "Estandarización de teléfonos" abajo.
>
> **Continuación 3 (misma fecha):** **notificaciones** — gafete + **protocolo** ahora se adjuntan por
> correo **y WhatsApp** (media base64, sin exponer el QR), redacción profesional, y **fix**: cancelar una
> cita ya no reenvía la invitación (manda aviso de cancelación). Ver la sección "Notificaciones" abajo.
>
> **Continuación 4 (2026-07-14):** **auditoría de doble canal en notificaciones** — se revisó el
> inventario completo de notificaciones (citas ×5, eventos ×5, documentos, y los 4 wrappers de
> `common/emails.py`). Todas mandaban correo **+ WhatsApp** salvo una: la **verificación de correo**
> (`enviar_verificacion_email`) solo iba por email. Se le agregó `telefono` opcional + WhatsApp
> best-effort, y se cablearon sus dos llamadores (alta pública y **reenviar-verificación** del
> super-admin) para pasar el teléfono del admin. Billing/webhooks de Stripe no emiten notificaciones
> al usuario (el dunning se aplica por middleware con 423), así que no había brecha ahí. Test nuevo
> `tests/test_emails_dual_canal.py` (8) fija la regla para los 4 wrappers. Regla registrada:
> **toda notificación va por correo y WhatsApp si el destinatario tiene ambos configurados.**
>
> **Continuación 5 (2026-07-14):** **Bitácora de accesos AL SISTEMA** (feature nueva) — los admins del
> tenant ahora tienen un historial de **autenticación**: modelo `config.BitacoraAcceso` (login /
> logout / intentos fallidos, con **IP + dispositivo**, para los dos contextos: *acceso* y
> *proveedores*). Servicio `registrar_acceso` (best-effort, se salta el schema public) enganchado en
> `common/auth_api.py` (`BaseLoginView` OK/fallido + `LogoutView`). `SuperAdminLoginView` sobrescribe
> `post` → el control plane no entra aquí. API solo-admin `/api/accesos-sistema/` (filtros
> evento/contexto/éxito/fecha) + página **Accesos al sistema** en frontend-acceso (nav admin). Migración
> `config.0003_bitacoraacceso` (--tenant). Tests `tests/test_bitacora_acceso.py` (6: login OK/fallido/
> correo-inexistente/cuenta-inactiva, skip en public, aislamiento). **Ojo — tres bitácoras distintas:**
> `HistorialCambio`=cambios de datos · `acceso.RegistroAcceso`=accesos físicos (escáner) ·
> `config.BitacoraAcceso`=accesos al sistema (autenticación).

---

## Cambios de esta sesión (commits en `origin/main`)

```
90e031b feat(admin): reenviar y verificar manualmente el correo del admin del tenant
c85110f docs: seguimiento del Connector (XCC) en STATUS + refresco de próximos objetivos
9779985 fix(mfa): no persistir el secreto TOTP hasta confirmar el enrolamiento
d206995 chore(dev): pre-commit hook con ruff (format + check --fix) via docker
f5bfd00 style: aplicar ruff format (arregla CI: ruff format --check)
```

## Estado por área (cambios de esta sesión)

| Área | Estado | Notas |
|---|---|---|
| MFA (enrolamiento TOTP) | ✔ arreglado | El secreto se guarda **en cache** (`_ENROL_TTL=600s`), no en BD, hasta que `ActivarTOTPView` confirma el 1er código. Un enrolamiento abandonado ya no deja al actor "a medio enrolar". `common/mfa_api.py`. **QA #2 cerrado** (el super-admin completó el enrolamiento y entró al dashboard). |
| Verificación de correo del admin (super-admin) | ✔ + tests | 3 acciones nuevas en `TenantAdminViewSet` (control plane) que entran al schema del tenant. Tarjeta en `frontend-admin/TenantDetalle.tsx`. Red de seguridad para el onboarding si el correo no llega. |
| Pre-commit hook | ✔ | `.githooks/pre-commit`: corre `ruff format` + `ruff check --fix` sobre los `.py` staged de `backend/` dentro del contenedor, re-stagea, y bloquea si queda lint no auto-corregible. Activar: `git config core.hooksPath .githooks`. |
| CI | ✔ (verde) | Se arregló la corrida roja de `ruff format --check`. El hook previene recurrencia. |
| Connector (XCC) | doc | Estado real ahora documentado en STATUS (F-D implementado + con tests; F-C en repo `xenty-connector`; F-E pendiente). |

---

## Feature nueva: verificación de correo del admin del tenant (detalle)

**Problema que resuelve:** en el alta pública (`SignupView`, `verificar_email=False`) el admin del
tenant queda con doble opt-in pendiente. Si el correo no llega (spam, typo, SMTP), queda **bloqueado
por el permiso DRF `EmailVerificado`** y no puede operar. El super-admin ahora lo destraba desde el
control plane.

**Backend — `backend/apps/tenants/admin_api.py`, `TenantAdminViewSet`** (3 `@action` detail):

| Acción | Método · ruta | Qué hace |
|---|---|---|
| `verificacion` | `GET .../verificacion/` | Lista los administradores del tenant y su estado (`verificado: bool`). |
| `reenviar_verificacion` | `POST .../reenviar-verificacion/` | Reenvía el correo de verificación (plantilla de marca) a los admins pendientes. |
| `verificar_email` | `POST .../verificar-email/` | Marca `email_verificado = now()` a los pendientes (fallback sin correo). Registra en `HistorialCambio` (con `usuario=None`, porque el actor es super-admin del control plane, no un `Usuario` del tenant). |

- Helper `_admins(tenant, solo_pendientes=)` filtra `Usuario.objects.filter(rol=ADMINISTRADOR,
  activo=True)`; con `solo_pendientes` añade `email_verificado__isnull=True`.
- **Las 3 acciones entran a `schema_context(tenant.schema_name)`** porque `accounts.Usuario` vive en
  el schema del tenant, no en `public`. Los permisos siguen siendo `IsAuthenticated + MFASesionCompleta
  + EsSuperAdmin`.
- Ambas acciones POST son **idempotentes**: si no hay pendientes responden 200 con lista vacía.

**Frontend — `frontend-admin/src/pages/TenantDetalle.tsx`:** tarjeta "Verificación de correo del
administrador" con la lista de estado + botones **Reenviar verificación** y **Verificar manualmente**.

**Tests — `backend/tests/test_tenant_verificacion_admin.py`** (3): lista pendiente, reenvío (usa
`mailoutbox`, valida `alternatives` = plantilla HTML), y verificación manual idempotente. Fixture
`tenant_sin_verificar` **module-scoped** (provisiona con `verificar_email=False`; drop de schema en
teardown).

---

## Connector (XCC) — F-E (repo `xenty-connector`)

> El Connector vive en un **repo separado**: `C:\Users\ADMIN\Documents\ProyectosElevation\xenty-connector`
> (Node 20 + TS + Fastify + Baileys). El repo principal NO depende de él (failover a UltraMsg/Sandbox).

**Qué se hizo** (commit `cd2c85e` en `xenty-connector`, ya pusheado a
`github.com/ElevationStudioMX/XentyC`):
- El anti-replay pasó de un `Map` en proceso a una **interfaz `NonceStore`** con dos implementaciones
  elegidas por `XCC_REDIS_URL`:
  - `InMemoryNonceStore` — comportamiento actual (una sola instancia).
  - `RedisNonceStore` — `SET NX PX` **atómico** compartido → permite desplegar **varias réplicas** del
    Connector sin aceptar replays entre ellas. Es el desbloqueo de la escala horizontal de F-E.
- `seen()` puede ser sync (memoria) o async (Redis); `auth.ts` hace `await`. **Fail-closed**: si Redis
  no responde, `seen()` lanza `NonceStoreUnavailableError` y `/v1` responde **503** (el Router del
  principal hace failover) en vez de arriesgar un replay. `commandTimeout=2000ms` acota la espera; se
  deja la cola offline (default) para no fallar durante la ventana de conexión inicial.
- `docker-compose.yml` del connector ahora incluye **su propio Redis** (sin persistencia: los nonces
  son efímeros), cableado por defecto (`XCC_REDIS_URL=redis://redis:6379` con override).
  `.env.example` documenta la variable (vacío = in-memory).

**Métricas Prometheus** (connector `b3f2f04`): `GET /metrics` (prom-client) con
`xcc_messages_total{tenant,type,result}`, `xcc_message_send_duration_seconds`, `xcc_sessions{state}`
(gauge calculado por scrape) + métricas del proceso Node. Sin auth por defecto; `XCC_METRICS_TOKEN`
opcional exige `Authorization: Bearer`.

**Webhook de estados de entrega** (connector `b3f2f04` emite + principal `ade929e` recibe):
- Connector: `SessionManager` engancha `messages.update` de Baileys, mapea el status numérico a
  `delivered/read/failed` y hace `POST` firmado HMAC (mismo esquema que `/v1`) a `XCC_WEBHOOK_URL`
  (opcional; sin la var no emite nada). Correlación por `message_id`. Best-effort.
- Principal: `POST /api/mensajeria/connector/webhook/` (control plane, `urls_public`), verifica
  HMAC+ventana+nonce (cache Redis) y actualiza `DestinatarioMensaje` por `external_id`. `Estado` gana
  `entregado`/`leido` (**migración `mensajeria.0005`** — ya aplicada al DB dev). **Solo avanza** el
  estado (delivered tardío no pisa read). Endpoint idempotente.

**Routing sticky / propiedad de sesión** (connector `f720b20`): con varias réplicas, cada sesión
`(tenant, connection_id)` tiene **un único dueño** (lock Redis `SET NX` + heartbeat, clave
`xcc:owner:{tenant}:{connection_id}`); `sendMessage` a un no-dueño → `409 { owner }`. El
`ConnectorProvider` del principal envía `X-XCC-Connection` para el hash consistente del ingress. Sin
Redis = una sola instancia (sin cambios). Config: `XCC_INSTANCE_ID`, `XCC_OWNER_TTL_SEC`.

**`connection_id` configurable por tenant** (principal `e67e382`): `PreferenciaMensajeria.connection_id`
(**migración 0006**), el Router instancia el `xcc` con él; API + pantalla "Mensajería · Proveedores"
lo exponen (campo con Ayuda, validado).

**Deploy** (connector `cbf89dc`, `1634a0f`): **artefactos listos** — `DEPLOY.md` (runbook),
`docker-compose.prod.yml` (puerto en loopback tras reverse proxy, redis, restart always) y
`nginx.xcc.conf.example` (TLS + `/metrics` restringido + upstream con hash por `connection_id`).
**Decisión DEC-008:** el XCC va en el **mismo CD** que el principal pero como **servicio opcional
(opt-in)**; en prod puede no levantarse y su ausencia no afecta al principal (master switch + failover).
**Verificado end-to-end en host local (staging, 2026-07-13):** `docker compose -f docker-compose.prod.yml
up` → connector + redis healthy; arranque con nonce+ownership en Redis; contrato HMAC vivo
(unsigned→401, firmado→200, replay→401, `/metrics` con token). **Interop bidireccional**: main→XCC
(`ConnectorProvider` firma OK → XCC responde 409 por sesión no escaneada) y XCC→webhook del principal
(endpoint vivo, exige HMAC → 401). El `ConfiguracionConnector` del dev quedó apuntando al XCC local
(`host.docker.internal:8090`, master switch ON) — no afecta a los tenants salvo que agreguen `xcc` a su
orden de proveedores. **Falta solo provisionar en un host de producción** (mismo bloqueo que el CD del
principal). Para stop: `docker compose -f docker-compose.prod.yml down` en `xenty-connector`.

**Pantallas de vinculación de WhatsApp** (principal `6a10439`): los usuarios ya **no necesitan CLI**
para vincular el número. El navegador nunca ve el secreto HMAC — el backend firma por él
(`apps/mensajeria/connector_client.py`, reusa la firma de `ConnectorProvider`):
- **Admin del tenant** (frontend-acceso, *Mensajería · Proveedores*): tarjeta "WhatsApp del Connector"
  con estado, botón **Vincular** → QR con polling hasta conectar, y **Desvincular**. Endpoints
  `/api/mensajeria/whatsapp/sesion/` (GET/POST/DELETE) + `/qr/` (conexión = `PreferenciaMensajeria.connection_id`).
- **Super-admin** (frontend-admin, *Comunicaciones*): sección "Sesiones por tenant" (tenant + conn →
  vincular/estado/QR/desvincular). Endpoints `/api/admin/comunicaciones/sesion/` + `/qr/`.
- Tests: 5 (`test_connector_sesiones.py`). Verificado en vivo: el proxy firmado alcanzó el XCC local y
  devolvió la sesión de `museos` (200). Ambas SPAs compilan.

**XCC como servicio del compose del principal** (perfil `connector`, DEC-008): el XCC está en
`docker-compose.yml` del principal (build `../xenty-connector`, mismo network, comparte el redis del
stack). Se levanta con `docker compose --profile connector up -d --build connector`; `docker compose up`
normal lo ignora. En local la URL base en *Comunicaciones* es **`http://connector:8090`** (ya no
`host.docker.internal`). Requiere `XCC_HMAC_SECRET` en el `.env` del principal (= hmac_secret de
*Comunicaciones*). Verificado: proxy POST → 201 por la red interna.

**Fix de envío — validación de número** (connector `a2fecbf`): antes se enviaba a ciegas y un número
sin lada/inexistente devolvía 202 "sent" pero no llegaba (falso éxito en el ledger). Ahora
`resolverDestino()` consulta `onWhatsApp` antes de enviar: no registrado → **422** (ledger ok=False,
fallo visible); registrado → usa el JID canónico (normaliza formato MX). **Los teléfonos deben ir con
lada de país** (52 + 10 dígitos). Diagnóstico del caso: una cita con un asistente de 10 dígitos sin
lada → el connector la aceptó pero WhatsApp no la entregó.

**Tres gotchas de dev resueltos hoy:** (1) la URL base NO puede ser `127.0.0.1`/`localhost` (dentro del
contenedor apunta al backend, no al XCC) — con el perfil es `http://connector:8090`. (2) el `backend`/
`superadmin-backend` corren con `runserver --noreload`: **tras agregar rutas/vistas hay que reiniciar**
esos servicios **y también nginx** (cachea la IP del upstream al arrancar; si reinicias los backends y
no nginx, la UI da 404/502 — p. ej. "no me deja entrar al tenant"). Comando:
`docker compose restart backend superadmin-backend nginx`.

**Verificación:**
- **Connector** (contenedor `node:20-slim`, Node no está en el host): `typecheck` + `build` limpios;
  `npm test` → **29 tests** (nonce/metrics/webhook/ownership/server); integración Redis (nonce +
  propiedad de sesión) verificada contra `redis:7-alpine` real.
- **Principal** (`docker compose exec backend pytest`): `test_connector_webhook.py` **5/5** +
  `test_connector_provider.py` **7/7** (incl. connection_id por tenant); suite sin aislamiento **64
  verdes**; migraciones `mensajeria.0005`/`0006` aplicadas; `ruff` limpio (pre-commit OK).

**Cómo correr el connector** (recordatorio; Node solo vía Docker en esta máquina):
```bash
cd ../xenty-connector
docker run --rm -v "$PWD:/app" -w /app node:20-slim sh -c "npm install && npm test && npm run build"
# integración Redis: red docker + redis:7-alpine + -e XCC_TEST_REDIS_URL=redis://<host>:6379
cp .env.example .env   # define XCC_HMAC_SECRET; docker compose up levanta connector + redis
```

## Estandarización de teléfonos — 10 dígitos (lada solo al enviar) — continuación 2026-07-13

**Motivo (pedido del usuario):** Xenty solo opera en México → no tiene sentido pedir `52 + 10 dígitos`
en la captura. **Formato canónico almacenado = 10 dígitos, sin lada.** La lada mexicana se antepone
**únicamente al enviar por WhatsApp**. Esto **supera** la guía del fix anterior ("los teléfonos deben
ir con lada"): ahora el usuario captura 10 dígitos y el sistema pone la lada solo.

**Punto único — `backend/common/phone.py` (nuevo):**
- `normalizar_telefono(v)` → 10 dígitos canónicos; quita lada (`52`/`52 1`), espacios, `+`, símbolos;
  `""` si no quedan exactamente 10 dígitos (inválido/incompleto).
- `formato_whatsapp_mx(v)` → `521` + 10 dígitos (JID canónico de WhatsApp MX; UltraMsg y el Connector
  lo aceptan, el XCC lo resuelve con `onWhatsApp`). Idempotente. `""` si el número es inválido.
  **Para cambiar el formato de envío (p. ej. quitar el `1` de móvil), este es el único sitio.**
- `TelefonoField(serializers.CharField)` → normaliza en `to_internal_value`; rechaza con error claro
  ("Ingresa un teléfono de 10 dígitos (sin lada)"); deja pasar vacío/nulo. No fija `max_length` (para
  no rechazar la entrada cruda con lada/espacios antes de normalizar).

**Entrada (normaliza + valida) — `TelefonoField` aplicado en los serializers:** `citas` (Contacto,
AsistenteCitaInput, AsistenteCita), `proveedores` (Proveedor.telefono, Onboarding.telefono_empresa +
whatsapp), `accounts` (UsuarioCreate + UsuarioUpdate), `recintos` (Recinto/Zona/Acceso), `empleados`
(Empleado). Todo lo que capture teléfono se guarda a 10 dígitos.

**Salida (antepone lada) — punto de envío:** `apps/mensajeria/services.py::notificar_whatsapp` (único
helper de notificación) y `procesar_envio` (campañas) llaman `formato_whatsapp_mx`. Un número inválido
se **omite** (no se manda un destino imposible → no más falsos "enviado"). También se arregló
`documentos/services.py`: llamaba a un `obtener_whatsapp()` **inexistente** (silenciado por try/except,
nunca enviaba) → ahora usa `notificar_whatsapp`.

**Frontend (4 SPA, campos de teléfono):** placeholder `5512345678`, ayuda "10 dígitos, sin lada. Ej.
5512345678", `onChange` que limpia con `replace(/\D/g,"").slice(0,10)`, `maxLength={10}`,
`inputMode="numeric"`. En `Onboarding.tsx` (proveedores) se añadió validación de 10 dígitos a
`telefono_empresa` y `whatsapp`. NO se tocaron los `replace(/\D/g,"")` de OTP/TOTP/NSS.

**NO se cambió el ancho de columna** (`telefono` sigue `CharField(max_length=30)`): 10 dígitos caben de
sobra y evita migraciones en 6 apps × schemas de tenant. Los datos legados con lada se normalizan al
re-guardarse, y el envío los normaliza igual (defensa en profundidad). **Sin migraciones.**

**Verificación:** `test_phone.py` (14: normalizar/formato/`TelefonoField`/`notificar_whatsapp` antepone
lada y omite inválidos). Suite sin aislamiento **83 verdes**; `ruff` limpio. Las SPAs `acceso` y
`proveedores` compilan (`tsc + vite build`).

---

## Notificaciones: adjuntos (gafete+protocolo) por correo y WhatsApp + fix de cancelación — continuación 2026-07-13

**Pedido:** (1) adjuntar gafete y **protocolo** a las invitaciones (el protocolo no se adjuntaba en
ningún lado) por correo **y WhatsApp**; (2) redacción profesional con toda la información; (3) al
**cancelar una cita** la notificación no correspondía a una cancelación (verificar eventos). Decisión del
usuario: adjuntos por **correo + WhatsApp** y aplicar a **citas y eventos**.

**Media por WhatsApp sin URL pública (base64).** El `archivo` del contrato de proveedores era una URL; el
gafete se genera como bytes y exponerlo en una URL pública chocaría con la regla de "auth+policy en toda
descarga" (lleva QR firmado). Solución: nueva `AdjuntoWhatsApp(nombre_archivo, contenido, mimetype,
caption)` (`apps/mensajeria/proveedores.py`) que se manda como **base64**:
- **ConnectorProvider** → `media_b64` + `type=image|document` (el XCC lo acepta nativo; `maxMediaBytes`
  16MB). Sin hosting ni exponer el QR firmado.
- **UltraMsg** → base64 en `messages/image` | `messages/document`.
- **Sandbox** → lo ignora (dev).
- El **Router** pasa `adjunto` solo cuando existe (no rompe firmas/dobles antiguos).

**`notificar_whatsapp(telefono, cuerpo, archivo=None, adjuntos=None)`** manda **el texto primero** (así la
info llega aunque la media falle) y luego cada adjunto como mensaje de media **best-effort**. Helper
`adjunto_protocolo(protocolo)` lee el PDF y lo envuelve (reutilizado por correo y WhatsApp).

**Citas (`apps/citas/services.py`, reescrito):** invitación a asistentes y a proveedor con **redacción
profesional** (bloque de detalles: fecha, hora, recinto, área, punto de acceso, protocolo; instrucción de
gafete; INE si aplica; vigencia). Gafete (imagen) + protocolo (PDF) adjuntos por **correo y WhatsApp**.
Nueva `enviar_cancelacion_cita()` con aviso de cancelación (sin gafete: "queda sin validez").

**Fix de cancelación (`apps/citas/views.py`):** `perform_update` detecta la **transición** de estado a
`CANCELADA` (cancelar = `PATCH estado=cancelada`) y envía el aviso de cancelación en vez de reenviar la
invitación; editar una cita ya cancelada no reenvía nada. **Eventos ya estaba bien** (acción `cancelar`
dedicada → `notificar_evento_cancelado`; borrar invitación → `notificar_invitacion_cancelada`).

**Eventos (`apps/eventos/services.py`):** invitación a proveedor y asignación a empleado ahora adjuntan el
**protocolo** (`ep.protocolo` o `evento.protocolo`, helper `_protocolo_de`) y mandan el gafete/pases de
estacionamiento por **WhatsApp** además del correo, con redacción profesional.

**Verificación:** `test_notificaciones_adjuntos.py` (11) + `test_connector_provider.py::test_connector_media_b64`.
Suite sin aislamiento **92 verdes**; `ruff` limpio; `manage.py check` sin issues. Generación del gafete
probada en vivo (24KB PNG). **Sin migraciones.** La media es best-effort: si un adjunto excede el límite o
el proveedor la rechaza, el **texto profesional ya se entregó**.

---

## Citas: alta/baja de asistentes (baja lógica) — continuación 2026-07-13

**Pedido:** en citas poder **dar de baja** y **agregar** asistentes a una cita existente; baja lógica
(no borrado físico). Decisión del usuario: en citas se mantiene el botón «Eliminar» físico de la cita;
en **eventos, nada por ahora** (el Evento ya se cancela por estado).

**Hallazgo que de-riesga:** el escáner **ya** respeta el estado del asistente
(`apps/acceso/services.py`): deniega con *"El invitado fue dado de baja de la cita"* cuando
`asistente.estado == CANCELADO`. El mecanismo de baja lógica ya estaba cableado; solo faltaba
exponerlo.

**Backend:**
- `AsistenteCitaViewSet.perform_destroy` → **baja lógica**: marca `estado=CANCELADO` (no borra), audita
  en `HistorialCambio` y avisa al asistente (`enviar_baja_asistente`). Reactivar = `PATCH {estado:0}`.
- `CitaViewSet` acción **`agregar-asistentes`** (POST `{asistentes:[...]}`): crea los invitados y envía
  la invitación **solo a los nuevos** (`enviar_invitacion_asistentes`). Bloquea walk-in y cita cancelada.
- `CitaSerializer._guardar_asistentes` ahora **devuelve** los creados. `_notificar_asistentes(cita,
  asistentes=None)` acepta subconjunto (None = activos, excluye CANCELADO). Nuevo `enviar_baja_asistente`.
- Guard de borrado de cita Directa: excluye asistentes CANCELADO (una cita con todos dados de baja sí se
  puede borrar).

**Frontend (`Citas.tsx`):** en el detalle, botón **Dar de baja / Reactivar** por asistente, y sección
**Agregar invitados** (reusa el autocomplete de personas). Se extrajo `invitadoRows()` para no duplicar.

**Dedup de invitados (regla de dominio):** `_guardar_asistentes` **no duplica** por **email o teléfono**
—contra los asistentes activos de la cita y dentro del mismo lote— (un CANCELADO no bloquea el realta);
`agregar-asistentes` responde `{agregados, omitidos}` y la UI lo informa. En el **autocompletado** de
personas, quien ya está en la cita (o ya en el lote) sale marcado *"· ya agregado"* y **no es
seleccionable** (`yaAgregado`/`mismaPersona` en `Citas.tsx`, compara por email/teléfono). **Eventos ya
dedup por FK** (`get_or_create` + `unique_together`). Es una validación "obvia" que va de oficio (ver
memoria del usuario: implementar validaciones evidentes sin preguntar).

**Verificación:** `test_citas_asistentes.py` (4, DB) + 2 de servicio en `test_notificaciones_adjuntos.py`.
Suite sin aislamiento **98 verdes**; `ruff` limpio; `manage.py check` OK; `frontend-acceso` compila.
**Sin migraciones** (se reusa `AsistenteCita.estado=CANCELADO`).

---

## Fix WebAuthn: RP ID / origin derivados del Host — continuación 2026-07-13

**Síntoma:** registrar una llave (passkey/FIDO2) fallaba en super-admin **y** tenant con "No se pudo
registrar la llave (cancelada o no compatible)" (0 registradas).

**Causa:** la config era estática — `WEBAUTHN_RP_ID="localhost"` y
`WEBAUTHN_ORIGINS="http://localhost:8080,…"`. Pero la app se sirve en **subdominios**
(`admin.localhost:8080`, `<slug>.localhost:8080`). Un `rp.id="localhost"` no es válido para un origen
`admin.localhost` → `navigator.credentials.create()` lanza `SecurityError` en el navegador → el
frontend cae al catch "(cancelada o no compatible)". Además `expected_origin` no incluía los subdominios.

**Fix:** el RP ID y el origen se **derivan del Host de la petición** (`common/webauthn.rp_desde_host`),
que ya viene validado por `ALLOWED_HOSTS` + django-tenants. `admin.localhost:8080` → rp_id
`admin.localhost`, origin `http://admin.localhost:8080` (nginx reenvía `Host: $http_host`, con puerto →
coincide exacto con el origen del navegador). Las 4 vistas (`common/webauthn_api.py`) pasan
`rp_id`/`origins` a las funciones (que mantienen el default de settings para tests/callers sin request).
Funciona igual en prod (`admin.xenty.mx`, `<slug>.xenty.mx`; `SECURE_PROXY_SSL_HEADER` ya da `https`).
Cada actor registra su credencial contra **su** subdominio (correcto: ahí inicia sesión).

**Verificación:** `test_webauthn.py` +2 (`rp_desde_host`, `opciones_registro` con rp_id del Host) → 8
verdes; `ruff` limpio. Probar en vivo: reintentar "Registrar llave" en `admin.localhost:8080` y en el
tenant. `WEBAUTHN_RP_ID`/`WEBAUTHN_ORIGINS` quedan solo como fallback; ya no hay que tocarlos por dominio.

---

## TOTP "fantasma" en tenant + Desactivar TOTP — continuación 2026-07-13

**Síntoma:** en el tenant, TOTP salía "Activado" (botón "Reconfigurar") aunque el usuario nunca lo
configuró.

**Causa:** dato viejo. En museos, `manuel@elevation.com.mx` tenía `mfa_totp_secret` **persistido** (del
código anterior al fix de cache) con `mfa_habilitado=False`. La UI del tenant deriva "Activado" de
`totp_habilitado = bool(mfa_totp_secret)` (`MeView`), así que un secreto huérfano se veía como activado
aunque el MFA no se enforce. Se **limpió** ese secreto en dev (`mfa_totp_secret=None`; sin WebAuthn →
`mfa_habilitado=False`).

**Gap de raíz (arreglado):** no había forma de **desactivar** TOTP desde la UI (solo "Reconfigurar").
Nuevo `DesactivarTOTPView` en `common/mfa_api.py` (compartido) → borra el secreto y pone
`mfa_habilitado = (tiene WebAuthn)`; idempotente. Rutas: `api/auth/mfa/totp/desactivar/` (tenant) y
`api/admin/mfa/totp/desactivar/` (control plane). Botón **Desactivar** (rojo, junto a Reconfigurar) en
`frontend-acceso/Seguridad.tsx` y `frontend-admin/Seguridad.tsx`, visible solo cuando TOTP está activo.

**Verificación:** `test_mfa_totp.py` (2: desactivar apaga MFA sin WebAuthn / lo conserva con WebAuthn) +
webauthn 8 → 10 verdes; `ruff` limpio; ambas SPAs compilan. **Sin migraciones.**

---

## Rediseño de correos: plantilla unificada «Xenty Accesos» (oscura) — continuación 2026-07-13

**Pedido:** reemplazar todos los templates de correo por una plantilla unificada oscura (referencia
`Email Xenty.dc.html`, 6 tipos), sin cambiar la lógica; quitar links de "Cancelar suscripción"/"Soporte"
del pie.

**`common/email_builder.py::construir_correo` rediseñado** (único shell de todos los correos):
cabecera con logo + barra de acento + hero (ícono + título + subtítulo) + **tarjeta de datos** (filas
etiqueta/valor) + bloque de mensaje + CTA + pie. **Layout por tablas + estilos inline** (compatibilidad
Gmail/Outlook/Apple Mail; sin flexbox ni `<style>`). Registro `_TIPOS` con 6 acentos/íconos
(`acceso`, `parking`, `recordatorio`, `modificacion`, `alerta`, `bienvenida`) + `info` (neutro azul
para reset/verificación). `_SOLID` da color sólido de respaldo por tipo (Outlook no pinta gradientes →
la barra/botón no caen a dorado). Nuevos params: `tipo`, `titulo`, `subtitulo`, `filas` (`{label,valor,
color?,mono?,grande?,full?}`), `card_titulo`, `mensaje`, `pre_header`, `footer_legal`, `privacy_url`.
**Retrocompatible**: `saludo`+`parrafos` siguen funcionando (se renderizan como cuerpo bajo el hero).

**Llamadores mapeados a tipo:**
- **Citas** (`apps/citas/services.py`) → **tarjeta completa** (`filas` con Invitado/Responsable, Cita,
  Fecha, Hora, Recinto, Área, Punto, Protocolo): invitación asistente + nueva cita proveedor =
  `acceso`; cancelaciones + baja de asistente = `modificacion`. Se eliminó `_detalle_parrafos` (helper
  muerto).
- **Eventos** (`apps/eventos/services.py`) → shell + acento correcto (conserva su cuerpo de texto):
  invitación + asignación = `acceso`; invitación-cancelada/desasignación/evento-cancelado = `modificacion`.
- **`common/emails.py`** (wrappers): invitación/activación proveedor = `bienvenida`; verificación +
  reset de contraseña = `info`.
- **Documentos** (`apps/documentos/services.py`): verificado = `bienvenida`, rechazado = `modificacion`.

**Footer:** solo el link «Política de privacidad» (nunca "Cancelar suscripción"/"Soporte"). El
`texto_plano` (fallback y cuerpo de WhatsApp) **no cambió** en ningún correo.

**Logo Xenty en la cabecera** (en vez del texto "XENTY/Accesos"): se incrusta `backend/static/
xenty-white.png` (wordmark blanco, 178×50) como **imagen inline vía Content-ID** — el header emite
`<img src="cid:xenty-logo">` y `enviar_correo_html` adjunta el PNG con `Content-ID: <xenty-logo>` +
`Content-Disposition: inline` **solo si el HTML lo referencia**. Elegido CID (no URL pública ni
data-URI): se muestra por defecto en Gmail/Apple Mail/Mailpit, sin hosting, y **no interfiere con los
adjuntos reales** (gafete/protocolo, que siguen como adjuntos normales). Si el archivo del logo no está,
`_marca()` cae al ícono SVG + texto (fallback). Verificado: el MIME lleva el `Content-ID` inline; tests
de correo verdes. En el Artifact de preview el `cid:` se reemplaza por data-URI solo para poder verlo.

**Verificación:** suite sin aislamiento **105 verdes**; `ruff` limpio; render de los 6 tipos revisado
(preview publicado como Artifact). **Sin migraciones.** Los correos reales se ven en **Mailpit**
(`http://localhost:8025`) al disparar una notificación. Gotcha de la sesión: si Docker Desktop se
reinicia, el contenedor `backend` se recrea desde la imagen prod → reinstalar dev-deps
(`docker compose exec backend pip install -r requirements-dev.txt`) antes de correr ruff/pytest.

---

## Connector siempre activo tras reiniciar Docker — continuación 2026-07-13

**Síntoma:** el WhatsApp del Connector aparecía "Desconectado" tras reiniciar/relevantar los contenedores.

**Causa raíz:** el `connector` es un servicio con **profile** (`profiles: [connector]`, DEC-008). Un
`docker compose up -d` **sin** `--profile connector` recrea el resto del stack en una red nueva pero
**deja al connector en la red vieja** → no resuelve el host `redis` (`getaddrinfo ENOTFOUND redis` en
bucle). Con Redis inalcanzable, `/v1` falla-cerrado (503) y la sesión (ownership por Redis) no arranca →
"Desconectado". La **recuperación de sesión sí funciona** (creds persistidas en el volumen `xcc_data`;
al boot el connector loguea "restaurando sesión persistida" → "sesión conectada").

**Fix de raíz:** `COMPOSE_PROFILES=connector` en el `.env` (dev). Así `docker compose up -d` **normal**
incluye el connector, lo (re)crea en la **misma red** que redis, y la sesión se auto-recupera. Sigue
siendo profile (prod lo omite dejando `COMPOSE_PROFILES` vacío → DEC-008 intacto). Documentado en
`.env.example`. Verificado: `docker compose config --services` ya lista `connector`; sesión de museos =
`state:open, connected:true`. (Si Docker recrea la red, un `docker compose up -d` la reengancha; ya no
hace falta `--profile` ni `--force-recreate`.)

---

## nginx re-resuelve upstreams (tenant ya no se cae al recrear contenedores) — continuación 2026-07-13

**Síntoma recurrente:** "no me deja entrar a mi tenant" (502/404) tras reiniciar/recrear contenedores.

**Causa raíz:** `nginx/nginx.conf` usaba `proxy_pass http://backend:8000;` con el **host literal** →
nginx resuelve la IP del contenedor **una vez al arrancar** y la cachea. Al recrear un backend/front
(nueva IP), nginx seguía apuntando a la IP vieja → 502. El parche era `docker compose restart nginx`.

**Fix de raíz (en `nginx/nginx.conf`):** `resolver 127.0.0.11 valid=10s ipv6=off;` (DNS embebido de
Docker) + **hostname en variable** en cada `proxy_pass` (`set $u backend; proxy_pass http://$u:8000;`).
Con el host en variable, nginx **re-resuelve en tiempo de request** (TTL 10s) en vez de cachear al
boot → cuando un contenedor cambia de IP, nginx la reengancha solo en ≤10s **sin reiniciar nginx**.
Aplicado a los 3 server (landing/admin/tenant) y a todos los upstreams (backend, superadmin-backend,
frontends). El passthrough de URI no cambia (todos los `proxy_pass` eran "bare", sin path).

**Verificado:** recreé `backend` + `frontend-acceso` (IPs nuevas) y el tenant siguió respondiendo
(SPA 200, login llega al backend) **sin tocar nginx**. → El workaround "reiniciar nginx tras reiniciar
backends" queda **obsoleto**.

---

## Cita/Evento cancelado = terminal (no editar ni reenviar) — continuación 2026-07-13

**Pedido:** una cita o evento **cancelado** ya no debe poder **editarse** ni **reenviar notificaciones**.

**Backend (fuente de verdad):**
- Citas (`apps/citas/views.py`): `perform_update` **rechaza** (`PermissionDenied`) si la cita ya está
  `CANCELADA` (terminal; cancelar sigue permitido porque es la transición desde otro estado);
  `reenviar_invitacion` responde **400** si está cancelada. (`agregar-asistentes` ya lo bloqueaba.)
- Eventos (`apps/eventos/views.py`): `EventoViewSet.perform_update` rechaza si el evento está
  `CANCELADO`. `EventoProveedorViewSet.perform_create`/`perform_update` rechazan si el evento padre
  está cancelado (no se invita/reenvía a proveedores de un evento muerto). Las transiciones de estado
  ya eran terminales (`CANCELADO → ∅`).

**Frontend:** en la lista de **Citas** se ocultan **Editar** y **Reenviar** cuando `estado==cancelada`
(y el bloque "Reenviar invitación" del detalle); en **Eventos** se oculta **✎ Editar** cuando
`estado==cancelado`.

**Verificación:** `test_citas_asistentes.py` (+2: no-editar / no-reenviar) + `test_eventos_cancelado.py`
(no-editar). Tests verdes; `ruff` limpio; `frontend-acceso` compila. Sin migraciones.

---

## Contexto NO obvio (IMPORTANTE)

0. **El repo `xenty-connector` ya tiene remoto** (resuelto 2026-07-13):
   `https://github.com/ElevationStudioMX/XentyC.git` (org **ElevationStudioMX**, distinta del principal
   en `XentySaaS/XentyAccesos`). `main` sigue a `origin/main`; ambos commits pusheados (`4d0e592` MVP +
   `cd2c85e` nonce Redis). Identidad git local del repo: `ChuyHR <manuel@elevation.com.mx>`.

1. **El fix de MFA cambió el modelo del handoff anterior.** Ya **no** hay "TOTP reseteado a propósito":
   el enrolamiento es ahora **basado en cache**. `EnrolarTOTPView` genera el secreto y lo guarda en
   cache bajo `mfa:totp:enrol:{ctx}:{schema}:{user.pk}` (TTL 600s), **sin tocar la BD**;
   `ActivarTOTPView` lo lee de cache, verifica el 1er código y **recién ahí** persiste
   `mfa_totp_secret` + `mfa_habilitado=True`. Recargar el QR reutiliza el secreto en curso (no
   invalida el que ya escaneaste). El super-admin `admin@xenty.mx` **ya completó** su enrolamiento.
2. **Correo = Gmail real** (`.env`: `smtp.gmail.com:587`). Reenvíos de verificación salen al buzón real.
   Para QA offline: `.env` → Mailpit (`EMAIL_HOST=mailpit`, `EMAIL_PORT=1025`, `EMAIL_USE_TLS=False`) y
   `docker compose up -d --force-recreate backend`.
3. **Pre-commit hook**: no se activa solo tras `clone`. Cada quien corre una vez
   `git config core.hooksPath .githooks`. Necesita el contenedor `backend` **arriba** (usa
   `docker compose exec`); si Docker está apagado, el hook lo avisa y no bloquea el commit.
4. **`verificar-email` (manual) es un bypass del doble opt-in**: úsalo solo como fallback cuando el
   correo genuinamente no llega. Queda auditado en `HistorialCambio` del tenant.
5. **Connector (XCC)**: `apps/mensajeria` ya tiene el enchufe `connector_provider.py` + Router con
   failover (F-D, con tests). El **servicio** XCC vive en el repo separado `xenty-connector` (Node +
   Baileys). Falta **F-E** (nonce en Redis, repo remoto del connector, deploy) y **decidir el proveedor
   de WhatsApp** (ver abajo).
6. **CI ya existe**; falta **CD** (sin host de producción decidido — no arrancar hasta definirlo).

---

## Decisiones abiertas (requieren al usuario)

1. **Proveedor de WhatsApp** — hoy **UltraMsg** primario (~$39/mes, no-oficial). Opciones:
   (a) promover **XCC/Baileys** a primario (self-host, ~$0 + servidor, mismo riesgo de baneo), o
   (b) añadir **WhatsApp Cloud API oficial** (Meta, pago por conversación, sin baneo, requiere
   plantillas). El Router con failover ya soporta ambos caminos. Documentado en `docs/STATUS.md`.
2. **Destino de producción / CD** — bloqueado hasta elegir host (VPS/PaaS/K8s).

## QA E2E — estado

| # | Flujo | Resultado |
|---|---|---|
| 1 | Recuperación de contraseña (acceso + proveedores) | ✅ Completo (2026-07-10, stack real) |
| 2 | MFA super-admin (enrolar de cero) | ✅ **Completo** (usuario enroló y entró al dashboard) |
| 4 | Documentos legales (aviso + términos) | ✅ Completo (2026-07-10, endpoint público) |
| 3 | Onboarding nuevo tenant | ⏳ **Pendiente de clicks**: registrarse en `xenty.localhost:8080` con correo real. Si el correo no llega → destrabar con la feature nueva en `admin.localhost:8080` (Reenviar / Verificar manualmente). |

## Próximos pasos sugeridos

1. **Cerrar QA #3 (onboarding)** en el navegador — ya con la red de seguridad de verificación manual.
2. **Connector F-E: código completo** (nonce Redis, repo remoto, métricas, webhook de estados, routing
   sticky, `connection_id` por tenant, artefactos de deploy). Falta **provisionar el XCC en un host**
   (ver `xenty-connector/DEPLOY.md`; bloqueado con el CD del principal) y **resolver el proveedor de
   WhatsApp** (UltraMsg vs XCC-primario vs Cloud API).
3. **Definir host de producción → armar CD** (workflow deploy + nginx prod + serving `/media` con policy + secrets).
4. **Backfill de documentos legales** en staging/prod cuando existan (`python manage.py sembrar_documentos_legales`).
5. No bloqueantes: MFA obligatorio para `Usuario`/`CuentaProveedor` del tenant; hardening de logs PII
   (structlog); servicio externo de Mesa de Ayuda (ISSUE-006).

## Verificar servicios

```bash
docker compose ps                                                 # core Up
docker compose exec backend pip install -r requirements-dev.txt   # una vez (pytest no está en la imagen prod)
docker compose exec backend python -m pytest -q --ignore=tests/test_aislamiento_tenants.py
git config core.hooksPath .githooks                               # activar el pre-commit hook (una vez)
docker compose exec backend python manage.py sembrar_documentos_legales --schema <slug>   # backfill legal
```
