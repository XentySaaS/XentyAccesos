# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).
> Actualizado: **2026-07-08** (2ª tanda del día). El anterior está en
> `handoffs/history/HANDOFF_2026-07-08_a.md` (Connector F-B/C/D).

## Resumen ejecutivo

Sesión enfocada en el **baseline de cumplimiento/seguridad (bucket #2)**. Sobre el trabajo previo
(producto F0–F8 completo + Connector de WhatsApp F-A→F-D), se cerraron:

1. **ARCO / LFPDPPP** (`apps.cumplimiento`): motor de derechos del titular — **export** (acceso,
   descifra PII) y **cancelación** (anonimización in-place: sobrescribe PII, borra archivos privados,
   baja lógica, **preserva fila y bitácora**). `SolicitudArco` (con plazo legal 20 días) +
   `DocumentoLegal` versionado por tipo (aviso de privacidad + términos). UI "Privacidad · ARCO" en
   frontend-acceso. Titulares cubiertos: Empleado, CuentaProveedor, AsistenteCita.
2. **Onboarding de proveedores**: el Aviso de Privacidad y los Términos ahora son **enlaces legibles**
   (modal, leídos por token vía `DocumentoOnboardingView`), y **REPSE/SUA pasan a obligatorios**
   (cliente + serializer).
3. **WebAuthn (FIDO2 / passkeys)** como 2º factor de MFA para **super-admin y usuarios del tenant**,
   reutilizando el flujo de sesión del TOTP (`mfa="pending"→"ok"`). Backend compartido
   (`common/webauthn*`), credenciales por schema, y **UI de MFA nueva en frontend-acceso** (verificación
   post-login + página Seguridad) que antes no existía.

Todo **commiteado y pusheado** a `origin/main` (`a5bd9c9..0a379df`, 3 commits: cumplimiento, onboarding,
mfa). `ruff` + `tsc` limpios; tests nuevos verdes (ARCO 8, WebAuthn 6) + suites previas.

## Estado por módulo

| Área | Estado | Notas |
|---|---|---|
| Producto F0–F8 + 3 SPAs | ✔ | Completo |
| Connector WhatsApp (XCC) | ✔ F-A→F-D · falta F-E | Repo separado `../xenty-connector` (ver §NO obvio) |
| ARCO / LFPDPPP | ✔ | Export + cancelación + solicitudes + documentos legales |
| Onboarding proveedores | ✔ | Docs legales legibles + REPSE/SUA obligatorios |
| MFA | ✔ TOTP + WebAuthn | super-admin (control plane) y Usuario (tenant). **Falta**: CuentaProveedor sin UI de MFA |
| Tests | ✔ | ARCO 8, WebAuthn 6, connector-provider 5, router 9, aislamiento 9, F0 2 |

## Contexto NO obvio (IMPORTANTE)

1. **Cancelación ARCO = anonimización, NO borrado físico** (obligado por baja lógica + FKs `PROTECT`
   + retención legal). `apps/cumplimiento/arco.py`: sobrescribe PII a placeholder/null, borra archivos
   del disco privado por tenant, marca baja. Idempotente. La fila y la bitácora (`RegistroAcceso`) se
   conservan.
2. **`DocumentoLegal`** (schema tenant) es genérico por `tipo` (`aviso_privacidad`,
   `terminos_condiciones`), **versionado**: cada edición crea una versión nueva (histórico legal). El
   admin lo edita en "Privacidad"; el onboarding lo lee por token; hay endpoint público por tenant.
   Ya hay **plantillas de texto** listas (aviso + términos, con placeholders del recinto) — se
   generaron en chat esta sesión; aún no sembradas en ningún tenant.
3. **WebAuthn es 2º factor** (no passwordless). Credenciales por schema: `CredencialWebAuthnAdmin`
   (public, SuperAdmin) y `CredencialWebAuthn` (tenant, Usuario). Retos en cache (Redis, TTL 5 min).
   **En prod hay que fijar** `WEBAUTHN_RP_ID` al dominio real y `WEBAUTHN_ORIGINS` a los orígenes
   HTTPS de cada SPA (el navegador exige que RP_ID == dominio visible). Dev: `localhost`.
   La verificación E2E real de WebAuthn requiere un navegador con autenticador (no se puede vía curl);
   los tests cubren mi lógica, la cripto de attestation la valida `py_webauthn`.
4. **El Connector es un repo SEPARADO**: `C:\xampp\htdocs\xenty-connector` (git propio, rama `main`,
   **commiteado local, SIN push** — no tiene remoto aún). Node+Baileys. Firma HMAC que debe calcar
   `ConnectorProvider`: `HMAC_SHA256(secret, METHOD\nPATH\nTENANT\nTIMESTAMP\nNONCE\nSHA256HEX(body))`,
   cabeceras `X-XCC-*`, ventana 300s. `XCC_HMAC_SECRET` = `ConfiguracionConnector.hmac_secret`.
5. **`--noreload`** (gotcha vigente): el backend no recarga `.py` solo. Tras cambios:
   `docker compose restart backend superadmin-backend nginx`. El entrypoint corre migraciones al
   arrancar → tarda ~60-90s en levantar el runserver (health 000 mientras tanto; es normal).
6. **Nginx cachea la IP del backend**: tras reiniciar backend, reiniciar nginx o `/api/` da 502/404.
7. **Tests**: `docker compose exec backend pip install -r requirements-dev.txt` y luego
   `python -m pytest`. Crea schemas → lento (~2-3 min por archivo pesado).
8. **Onboarding sirve en AMBOS urlconfs**: las rutas `/api/onboarding/*` (incl. `documento/`) están en
   `config/urls_public.py` Y `config/urls.py` porque la SPA de proveedores vive bajo el subdominio del
   tenant. Al añadir una ruta de onboarding, ponerla en los dos.

## Próximos pasos sugeridos

1. **Baseline #2 restante**: backups/retención, SSO entre productos de la suite, notificaciones
   in-app, y el quick win de **reactivar `B904`** en ruff (hoy diferido).
2. **Connector F-E**: métricas Prometheus, webhook de estados de entrega, escala horizontal (nonce en
   Redis + routing sticky), `connection_id` configurable por tenant. Y **crear el repo remoto** del
   `xenty-connector` + push + deploy.
3. **MFA de CuentaProveedor** (proveedores): el backend TOTP/WebAuthn es genérico pero el ctx
   `proveedores` no está soportado en las vistas WebAuthn ni tiene UI de MFA en frontend-proveedores.
4. **Deploy a producción**: servir `/media` con `DEBUG=False`, Nginx prod + secrets, `WEBAUTHN_*` de
   prod, CI de deploy.
5. **Sembrar** el aviso/términos (plantillas ya redactadas) en los tenants y QA visual E2E autenticado.

## Verificar servicios

```bash
docker compose ps                                   # todos Up
docker compose restart backend superadmin-backend nginx   # tras cambios .py
docker compose exec backend pip install -r requirements-dev.txt && \
  docker compose exec backend python -m pytest tests/test_arco.py tests/test_webauthn.py -q
docker compose exec backend ruff check .            # bloqueante en CI
# rutas MFA WebAuthn (401 = auth requerida, ruta OK):
curl -s -o /dev/null -w "%{http_code}" -X POST -H "Host: rayados.localhost" \
  http://localhost:8002/api/auth/mfa/webauthn/registro/opciones/
```
