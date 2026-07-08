# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).
> Actualizado: **2026-07-08**. El anterior está en `handoffs/history/HANDOFF_2026-07-03.md`.

## Resumen ejecutivo

Sesión centrada en el **Xenty Communication Connector (XCC)** — el respaldo/failover de WhatsApp.
Se cerraron **F-B, F-C y F-D** de un tirón; el respaldo queda **operativo end-to-end** (solo falta
escanear un QR real para enviar de verdad — eso es operación, no código). Lo demás del producto
(F0–F8) seguía completo desde la sesión previa.

1. **F-B · Config por UI**: `ConfiguracionConnector` (global, super-admin, schema public: master
   switch + secreto HMAC cifrado + timeouts + umbrales de breaker) y `PreferenciaMensajeria` (por
   tenant, schema del tenant: orden de proveedores + failover + reintentos + timeout). El Router lee
   ambas (precedencia master switch → preferencia). APIs `/api/admin/comunicaciones/` (control plane)
   y `/api/mensajeria/preferencia/` (tenant, admin). Pantallas **"Comunicaciones"** (frontend-admin) y
   **"Proveedores WA"** (frontend-acceso, con Ayuda ⓘ).
2. **F-C · Connector MVP**: **repo separado** `xenty-connector` (Node 20 + TS + Fastify + Baileys).
   API REST `/v1` con HMAC+nonce, sesiones por `(tenant, connection_id)` con QR/pairing + reconexión +
   recuperación tras reinicio, **media completa**, persistencia por tenant, `/healthz`+`/v1/status`,
   logs sin PII. Verificado en Docker (healthz, 401/409, **QR real generado**).
3. **F-D · `ConnectorProvider` + failover real**: cliente REST del XCC en el principal
   (`apps/mensajeria/connector_provider.py`), registrado en `proveedores.registro_proveedores`. El
   Router hace **failover real** xcc→UltraMsg/Sandbox. **Interop en vivo Django↔XCC verificada**
   (firma Python aceptada por el Connector Node → 409 por sesión inexistente, no 401).

Tests verdes: backend `test_connector_provider` (5) + `test_mensajeria_router` (9) + aislamiento (9,
incluye preferencia por tenant); connector `vitest` (15). `ruff` + `tsc` limpios.

## Estado por módulo

| Área | Estado | Notas |
|---|---|---|
| F0–F8 producto + 3 SPAs | ✔ | Completo desde sesiones previas |
| Mensajería / Connector | ✔ F-A→F-D | Respaldo WhatsApp operativo; **falta F-E** (métricas/webhook/escala) |
| `xenty-connector` (repo separado) | ✔ F-C | `C:\xampp\htdocs\xenty-connector` · Node+Baileys · ver su `README.md` |
| Tests | ✔ | Backend (aislamiento 9 + router 9 + connector 5 + F0 2) · connector 15 (vitest) |

## Contexto NO obvio (IMPORTANTE)

1. **El Connector es un repo SEPARADO**: `C:\xampp\htdocs\xenty-connector` (git propio, rama `main`).
   NO vive dentro de este repo. Opcional: si no está levantado, el Router usa solo UltraMsg (failover).
2. **Esquema de firma HMAC XCC** (lo comparten `connector_provider.py` y `xenty-connector/src/hmac.ts`):
   `HMAC_SHA256(secret, f"{METHOD}\n{PATH}\n{TENANT}\n{TIMESTAMP}\n{NONCE}\n{SHA256_HEX(body)}")`,
   cabeceras `X-XCC-{Tenant,Timestamp,Nonce,Signature}`, ventana 300s, nonce single-use. Se firma y
   envía **el mismo cuerpo en bytes** (`data=`, no `json=`) para que el hash coincida byte a byte.
   `XCC_HMAC_SECRET` (env del connector) **debe** igualar `ConfiguracionConnector.hmac_secret` (UI).
3. **Master switch**: `ConfiguracionConnector.habilitado=False` apaga el Connector para todos al
   instante (rollback sin desplegar). El Router cachea el snapshot de config **20s** (Redis, por
   tenant) → los cambios del super-admin propagan en segundos.
4. **`connection_id`** del `ConnectorProvider` es `"principal"` por defecto (constante). Hacerlo
   configurable por tenant es parte de F-E.
5. **Interop/verificación local**: el backend (docker) alcanza un XCC levantado en el host vía
   `host.docker.internal:8091`. El 409 (sesión inexistente) es señal de éxito de auth; 202 real exige
   escanear el QR con un teléfono.
6. **`--noreload`** (gotcha vigente): el backend no recarga código Python solo. Tras cambios `.py`:
   `docker compose restart backend superadmin-backend nginx` (nginx por el punto #7). El entrypoint
   corre migraciones al arrancar (tarda ~30-60s en levantar el runserver).
7. **Nginx cachea la IP del backend**: tras reiniciar el backend, `docker compose restart nginx` o
   `/api/` da 502/404.
8. **Dev-deps para tests**: `docker compose exec backend pip install -r requirements-dev.txt` y luego
   `python -m pytest`. La suite crea schemas (lenta, ~3 min).

## Próximos pasos sugeridos

1. **F-E del Connector**: métricas Prometheus (`/metrics`), webhook de estados de entrega
   (delivered/read), escala horizontal (routing sticky por `connection_id` + nonce en Redis),
   `connection_id` configurable por tenant (hoy fijo `"principal"`).
2. **Operación real**: escanear el QR de una sesión (`POST /v1/tenants/{t}/sessions` → `GET .../qr`)
   para habilitar envíos reales por el Connector.
3. **Deploy del Connector**: contenedor propio con volumen de sesiones y `XCC_HMAC_SECRET` seguro;
   `url_base` accesible desde el backend. `xenty-connector` no tiene remoto git aún.
4. **Baseline pendiente** (heredado): servir `/media` en prod (`DEBUG=False`), WebAuthn opcional,
   ARCO/LFPDPPP, backups/retención, SSO entre productos, reactivar `B904`.

## Verificar servicios

```bash
docker compose ps                                   # todos Up
docker compose restart backend nginx                # tras cambios .py
docker compose exec backend pip install -r requirements-dev.txt && \
  docker compose exec backend python -m pytest tests/test_connector_provider.py tests/test_mensajeria_router.py -q

# Connector (repo separado):
cd ../xenty-connector && npm install && npm test    # 15 tests
docker build -t xenty-connector:test . && \
  docker run -d --name xcc -e XCC_HMAC_SECRET=dev -p 8091:8090 xenty-connector:test
curl -s -o /dev/null -w "%{http_code}" http://localhost:8091/healthz   # 200
```
