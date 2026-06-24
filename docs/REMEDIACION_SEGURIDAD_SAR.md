# REMEDIACION_SEGURIDAD_SAR — Hallazgos del origen → fix en el stack destino

> Cada hallazgo de la auditoría del SAR (PHP/Laravel, puntuación global **3.5/10**) mapeado a su
> remediación concreta en el stack Xenty (Django/DRF). **Contractual**: la reconstrucción no porta
> deuda; cada fix es requisito de la fase indicada y se verifica en su checkpoint.
>
> Referencia de `PLAYBOOK_SAR_XENTY.md` §7. Modelos en `MODELO_DATOS_SAR.md`. Cada ítem incluye:
> origen (dónde estaba), riesgo, **fix destino**, fase y criterio de verificación.

---

## 0. Resumen ejecutivo

| Severidad | Hallazgos | Concentración |
|---|---|---|
| Crítico | C1–C8 | Secretos en git, cripto casera de QRs, rutas sin auth, IDOR/PII |
| Alto | A1–A8 | Replay edge, INE en claro, uploads sin validar, sin rate limit, sin billing |
| Medio | M1–M8 | XSS, rutas duplicadas, validación hueca, paginación, código muerto |
| Bajo | varios | Código comentado, middleware esqueleto, `.env.example` incompleto |

Principio rector: la migración de stack es la **única** oportunidad limpia de cortar esta deuda de
raíz. Ningún patrón inseguro del origen se replica "porque así estaba".

---

## 1. Acciones día 0 (antes de cualquier despliegue del destino)

Independientes del código nuevo; se ejecutan al arrancar el proyecto:

1. **Rotar TODAS las credenciales heredadas** (estaban en git, §C1): bases de datos MySQL,
   SSH/IONOS, AWS (Textract/S3), Gmail/SMTP, UltraMsg (token + instance_id). Las del origen se
   consideran comprometidas.
2. **No portar `temporal/`** ni ningún `.env`, `links.text`, `cambios.sql`. Si el repo destino
   parte de un fork, purgar el historial (git filter-repo) antes del primer push.
3. **Eliminar `public/.env`** del concepto de despliegue: en Django no hay `.env` servible bajo el
   web root; Nginx sirve solo `/static` y `/media` controlados.
4. `DEBUG=False` por defecto fuera de dev; sin `.env` en imagen de contenedor (inyección por entorno).

---

## 2. CRÍTICOS

### C1 — Secretos versionados en git
- **Origen**: `temporal/.env.*`, `links.text` (credenciales IONOS/SSH/BD en claro), `public/.env`.
- **Riesgo**: compromiso total de infraestructura y cuentas de terceros.
- **Fix destino**: `python-decouple` + `.env` **no versionado**; `.env.example` documenta cada
  variable sin valores. Secretos por variable de entorno del contenedor/Azure. `SECRET_KEY` y
  `SECRET_KEY_FERNET` **separadas**, sin default (falla en arranque si faltan).
- **Fase**: F0. **Verificación**: `git ls-files | grep -E '\.env'` vacío; arranque falla sin secretos.

### C2 — Credenciales UltraMsg hardcodeadas
- **Origen**: `Whatsapp.php` (token e `instance_id` literales en el código).
- **Riesgo**: cualquiera con el repo envía WhatsApp a nombre de la empresa.
- **Fix destino**: cliente WhatsApp en `apps.mensajeria/services/whatsapp.py` detrás de interfaz;
  credenciales desde settings/`.env`. Rotar token. Posibilidad de credenciales por tenant en
  `Opcion`/config cifrada si se requiere multi-cuenta.
- **Fase**: F7. **Verificación**: grep de tokens literales = 0; envío usa credencial de entorno.

### C3 — Cifrado casero de QRs y tokens (el más grave)
- **Origen**: `EncryptionHerper.php` — **AES-128-ECB con clave fija `'Elevation2025'`** en git.
  ECB es determinístico, sin IV ni MAC. Protege el payload del QR (`id|contexto|tipo`) de los
  gafetes de acceso físico y el token de invitación de proveedor.
- **Riesgo**: **gafetes falsificables → acceso físico no autorizado**; tokens de invitación forjables.
- **Fix destino**:
  - QR de acceso: payload **firmado con HMAC-SHA256** (clave de servidor) o cifrado con **Fernet**
    (AES-128-CBC + HMAC, con IV), incluyendo `jti` único por emisión y `exp` (vigencia). El
    verificador valida firma + vigencia + pertenencia. Clave en `SECRET_KEY_FERNET` (no en código).
  - Tokens de invitación: `itsdangerous`/`TimestampSigner` o JWT corto firmado, con expiración 72h,
    verificable sin estado; o registro `InvitacionProveedor` con expiración en BD.
  - **Reemisión**: todos los QR del sistema viejo se invalidan; se reemiten al migrar (ver
    `MIGRACION_DATOS_SAR.md` §6, reemisión de credenciales).
- **Fase**: F1 (tokens), F5 (QR). **Verificación**: test "QR no forjable conociendo el código";
  manipular un byte del payload → rechazo; QR expirado → rechazo.

### C4 — Rutas operativas sin autenticación
- **Origen**: `GET /migrate` (corre `migrate --force`), `/clear-cache`, `/syncp` (resetea permisos),
  `/csrf-test`, `/test` (genera gafetes reales) en `routes/tenant.php`.
- **Riesgo**: cualquiera dispara migraciones, limpia cache o resetea permisos del tenant.
- **Fix destino**: **estas rutas no existen** como endpoints HTTP. Son management commands
  (`migrate_schemas`, `clearcache`) ejecutados por CLI/CD. No hay endpoint público que ejecute
  operaciones de mantenimiento.
- **Fase**: F0. **Verificación**: no existen rutas `/migrate`, `/syncp`, `/clear-cache`, `/test`, `/csrf-test`.

### C5 — IDOR y path traversal en visores de archivos
- **Origen**: `UtilsController` `viewFileRepse/Sua/Ine` reciben `{id}` de supplier y sirven el
  archivo **sin auth ni verificación de pertenencia**; `viewFileIneAsisten`/`viewFileDocumentEmployee`
  reciben `{path}` sin sanitizar (traversal). Imágenes INE enumerables.
- **Riesgo**: fuga de documentos fiscales y de identidad de cualquier proveedor/persona.
- **Fix destino**:
  - Archivos en **storage privado por schema** (`TenantFileSystemStorage`), nunca en `/media` público.
  - Descarga vía endpoint DRF con `IsAuthenticated` + **policy de pertenencia** (el recurso pertenece
    al tenant y el actor tiene rol/membresía); responde con URL firmada temporal o stream controlado.
  - Sin parámetros `{path}` crudos: se referencia por `id` de modelo; el storage resuelve la ruta.
- **Fase**: F1 (proveedor), F2 (docs empleado), F4 (INE). **Verificación**: acceso sin auth → 401/403;
  acceso a archivo de otro tenant → 404; no hay parámetro de ruta manipulable.

### C6 — Bypass de aislamiento de dispositivo (typo `whilere`)
- **Origen**: `LongPollController.php:109` `->whilere('device_tenant_id', ...)` — método inexistente;
  el filtro por dispositivo no se aplica.
- **Riesgo**: un dispositivo hace `ack` de comandos de otro dispositivo.
- **Fix destino**: en el endpoint de long-poll/ack (`apps.dispositivos`), filtrar `ComandoEdge` por
  `dispositivo == request.dispositivo_autenticado` de forma explícita y testeada; `select_for_update`
  al marcar `sent`/`ack` para evitar carreras.
- **Fase**: F6. **Verificación**: test — dispositivo A no puede `ack` comandos de B.

### C7 — Fuga cross-tenant en API de dispositivos
- **Origen**: `ApiDevicesController@validateQrCode/validateQrAE` obtiene el tenant del device pero
  **no verifica que el empleado/evento del QR pertenezca a ese tenant**.
- **Riesgo**: combinado con C3 (QRs forjables), enumeración de personas de otros tenants.
- **Fix destino**: el dispositivo está ligado a un `tenant_id` (en `public`). Toda validación de QR
  corre **dentro del `tenant_context` del dispositivo**; el QR firmado incluye el tenant y se rechaza
  si no coincide. Nunca se resuelven IDs fuera del schema del tenant del dispositivo.
- **Fase**: F6. **Verificación**: suite de aislamiento edge — QR de tenant X presentado a dispositivo
  de tenant Y → rechazo, sin filtrar datos.

### C8 — `APP_DEBUG=true`/`APP_ENV=local` en despliegue
- **Origen**: `.env` desplegado con debug activo → stack traces con SQL y paths.
- **Fix destino**: `DEBUG=False` salvo dev; `ALLOWED_HOSTS` explícito; páginas de error genéricas;
  Sentry captura el detalle (con scrubbing, §A7/12.5).
- **Fase**: F0. **Verificación**: respuesta de error en prod no expone traza.

---

## 3. ALTOS

### A1 — Replay attack en HMAC de dispositivos
- **Origen**: `VerifyDeviceHmac` valida firma sobre `METHOD-PATH-TIMESTAMP` con ventana 300s, **sin
  nonce** (usa `hash_equals`, eso está bien).
- **Fix destino**: middleware/authentication DRF HMAC con `hmac.compare_digest` + ventana de tiempo +
  **nonce/`jti` de un solo uso** (consumido en Redis con TTL = ventana). Reuso del nonce → rechazo.
- **Fase**: F6. **Verificación**: reenviar la misma petición firmada dentro de la ventana → rechazo.

### A2 — PII de INE en claro (BD + disco público)
- **Origen**: `ine_data` JSON plano en BD; imágenes en `storage public/ine_images/` (confirmado en
  `temporal/.../app/public/ine/`). Incumple LFPDPPP.
- **Fix destino**: `AsistenteCita.ine_data` → `EncryptedJSONField` (Fernet); `numero_identificacion`,
  `curp`, `nss` → `EncryptedCharField`; imágenes INE a **disco privado por schema**. Logs sin PII.
- **Fase**: F4 (+ re-cifrado en ETL, `MIGRACION_DATOS_SAR.md` §5). **Verificación**: inspección de BD
  muestra ciphertext; archivo INE no accesible por URL pública.

### A3 — Uploads sin validación MIME/extensión
- **Origen**: onboarding de proveedor usa `getClientOriginalName()` sin validar tipo/tamaño.
- **Fix destino**: validadores DRF de extensión + MIME real (python-magic) + tamaño máximo por tipo
  (docs ≤2MB, protocolos ≤10MB). Nombre de archivo generado por el servidor (no el del cliente).
- **Fase**: F1 (onboarding), F2 (docs), F3 (protocolos). **Verificación**: subir `.exe` renombrado a
  `.pdf` → rechazo.

### A4 — Sin rate limiting
- **Origen**: `/api/v1/*` (edge) y endpoints públicos de tenant sin límite.
- **Fix destino**: `django-ratelimit` con backend Redis. Edge por dispositivo/IP; login y reset de
  password con límites estrictos; onboarding público acotado.
- **Fase**: F0 (auth), F6 (edge). **Verificación**: superar el umbral → 429.

### A5 — Cache tenancy compartida
- **Origen**: `CacheTenancyBootstrapper` comentado → riesgo de cache entre tenants.
- **Fix destino**: `RedisCache` con **prefijo por schema** (key namespacing por tenant) garantizado
  por construcción; sin claves globales para datos de tenant.
- **Fase**: F0. **Verificación**: suite de aislamiento — escribir cache en tenant A no es legible en B.

### A6 — Sin enforcement de pago (trial/subscription comentado)
- **Origen**: `EnsureTenantIsActive` con el check comentado → ningún tenant se bloquea.
- **Fix destino**: control plane Xenty completo: middleware de ciclo de vida
  (`BloquearTenantsInactivos`, `BloquearTrialExpirado`, `EnforceModoSoloLectura`) gobernados por
  estado del tenant vía webhooks Stripe. Whitelist para que el cliente siempre pueda pagar.
- **Fase**: F0. **Verificación**: tenant `suspendido` → solo lectura; `trial` vencido → bloqueo con ruta de pago.

### A7 — Logs con PII
- **Origen**: flujo OCR loggea contexto; 15+ logs históricos en `storage/logs/`.
- **Fix destino**: `structlog` con processor de **redacción de PII** (RFC, CURP, email, INE) antes de
  emitir; Sentry `before_send=scrub_event`; sin logs de payloads de OCR.
- **Fase**: F0 (logging base), F4 (OCR). **Verificación**: log de un flujo OCR no contiene CURP/INE.

### A8 — `GET /test` genera gafetes reales públicos
- **Origen**: `FrontendController` ruta pública de prueba que emite credenciales.
- **Fix destino**: no existe; la emisión de gafetes es un servicio autenticado (`apps.gafetes`).
- **Fase**: F5. **Verificación**: no hay endpoint público de emisión.

---

## 4. MEDIOS

| # | Origen | Fix destino | Fase |
|---|---|---|---|
| M1 | XSS: `{!! $record->...data_text !!}` con datos de OCR | React escapa por defecto; sin `dangerouslySetInnerHTML`; si hay HTML, `rehype-sanitize` | F4 |
| M2 | Rutas duplicadas/conflictivas (`/employee-document/view`, `/print-badges`) | Router DRF único; sin rutas duplicadas; tests de routing | F2/F5 |
| M3 | `validaSeccionINE()` siempre `true` (validación hueca) | Implementar validación real de sección INE o eliminar el campo; no dejar validación falsa | F4 |
| M4 | `History::getHistory()` sin paginación (`->get()` total) | Paginación DRF estándar en historial; índices (`MODELO §8`) | F8 |
| M5 | `VerifyHmacSignature` (variante con secreto global) — código muerto | No portar; una sola vía HMAC (A1) | F6 |
| M6 | `/csrf-test` residuo de debugging | No existe | F0 |
| M7 | Lógica invertida en `PreventAccessFromTenantDomains` | Routing por subdominio de django-tenants (`urls.py`/`urls_public.py`) bien separado y testeado | F0 |
| M8 | Import faltante de `ZoneController` → error runtime | No aplica (reescritura); cobertura de tests evita rutas rotas | F1 |

---

## 5. BAJOS

- Código comentado masivo y middleware esqueleto (`EnsureUserIsActive`, `ProviderSessionMiddleware`):
  no se portan; el destino implementa solo middleware funcional.
- Manejo de errores inconsistente (`abort(404)` silencioso): DRF con exception handlers uniformes y
  logging estructurado.
- `.env.example` desactualizado: el destino mantiene `.env.example` **completo y verificado** como
  parte del DoD de F0 y F8 (toda variable usada está documentada).

---

## 6. Matriz hallazgo → fase (checklist de verificación)

| Hallazgo | Fase | Cerrado en checkpoint cuando… |
|---|---|---|
| C1, C4, C8, A4(auth), A5, A6, A7(base), M6, M7 | F0 | tests de aislamiento + arranque sin secretos + sin rutas peligrosas |
| C3(tokens), C5(proveedor), A3(onboarding) | F1 | onboarding con token firmado + archivos privados con policy |
| C5(docs), M2 | F2 | visor de docs con auth+pertenencia; sin rutas duplicadas |
| A3(protocolos) | F3 | validación MIME/tamaño de protocolo |
| A2, M1, M3, C5(INE) | F4 | INE cifrado + disco privado; sin XSS; validación INE real |
| C3(QR), A8 | F5 | QR firmado inviolable; sin emisión pública |
| C6, C7, A1, A4(edge), M5 | F6 | suite de aislamiento edge + anti-replay |
| C2 | F7 | WhatsApp sin credenciales hardcodeadas |
| M4, A7(OCR completo) | F8 | paginación + scrubbing PII verificado |

---

## 7. Pruebas de seguridad obligatorias (parte del DoD)

- **Aislamiento entre tenants** (datos, archivos, cache, comandos edge): un tenant nunca lee de otro.
- **QR**: manipulación de payload → rechazo; expiración respetada; tenant cruzado → rechazo.
- **Anti-replay edge**: nonce reutilizado → rechazo.
- **IDOR/traversal**: acceso a archivo ajeno o ruta manipulada → 403/404.
- **Uploads**: tipo/tamaño/MIME forzados.
- **PII**: ningún log ni respuesta de error contiene CURP/INE/RFC en claro; BD almacena ciphertext.

---

*Fin de la remediación. Acompaña a `MIGRACION_DATOS_SAR.md`, que aplica el re-cifrado de PII y la
reemisión de credenciales durante el traslado de datos.*
