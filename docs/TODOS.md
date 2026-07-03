# Tareas — Xenty Acceso

> Actualizado: 2026-07-03
>
> Reglas: `[x]` hecho · `[ ]` pendiente · `[~]` descartado/fuera de alcance. La sección **Baseline
> de la suite** son requisitos transversales que **todo producto Xenty** (Fiscal, Nómina, Acceso)
> debe cumplir; el resto es específico de Acceso.

---

## Baseline de la suite Xenty (transversal — todo producto debe tenerlo)

### Comercial / control plane
- [x] Billing Stripe (suscripción + paquetes de créditos + webhooks, modo sandbox)
- [x] Créditos con ledger append-only (`MovimientoCredito` / `SaldoCreditos`)
- [x] Panel super-admin (control plane): tenants, planes, detalle, gracia, checkout
- [x] Onboarding self-service (`/api/signup`) + landing pública separada
- [ ] **Mesa de Ayuda (Nivel B) completa** — hoy solo `SaludConfiguracionView` (stub). Falta la
      integración real (registro/consulta de tickets, credenciales por tenant cifradas). *Requisito
      explícito del playbook §5.*

### Identidad y seguridad
- [x] MFA TOTP (enrolar/activar/verificar) en control plane y tenant
- [ ] **MFA WebAuthn** — el playbook define MFA = TOTP **+ WebAuthn**; solo TOTP está hecho
- [x] Roles + permisos granulares (`RequiereRol` / `PermisoUsuario`)
- [x] Rate limiting (login, signup, onboarding, edge, ocr) + `Ratelimited`→429
- [x] Aislamiento multitenant probado (suite `pytest -k aislamiento`)
- [x] Passwords Argon2id · JWT blacklist+rotación · PII cifrada (Fernet)
- [x] Headers de seguridad en prod (`check --deploy` limpio)

### Observabilidad y operación
- [x] Sentry con scrubbing de PII (`before_send`) en prod
- [ ] **Logs estructurados con redacción de PII (structlog cableado)** — el processor
      `common/observability.procesador_structlog` existe pero **no está conectado** a `LOGGING`
- [ ] **Health / readiness endpoint** (`/health`, `/readyz`) — no existe; necesario para deploy,
      balanceador y monitoreo
- [ ] **Monitoreo de Celery** (estado de tasks/colas, alertas de fallo)
- [x] Versionado de releases (`Version` model + `docs/CHANGELOG.md`)

### Cumplimiento y datos (LFPDPPP / privacidad)
- [x] PII cifrada en reposo + archivos en disco privado por schema
- [ ] **Derechos ARCO / portabilidad**: exportar y **borrar** datos del titular a solicitud
- [ ] **Aviso de privacidad + Términos y condiciones** (legal, aceptación en onboarding)
- [ ] **Backups y política de retención** (respaldo por schema + restauración probada)

### Entrega
- [ ] **CI/CD pipeline** (lint + tests + build + deploy)
- [ ] Deploy a producción (Nginx prod, secrets por entorno, `DEBUG=False`)
- [ ] `requirements-dev.txt` reproducible en la imagen (hoy `pytest` se instala a mano)

---

## Cierre para producción (específico de Acceso)

- [ ] Terminar hardening: cablear structlog (PII en logs) + descarga `/media/` con policy de
      pertenencia (evitar servir archivos privados por URL directa) — ISSUE-004
- [ ] Verificar foto empleado end-to-end (fix ValueError aplicado) — ISSUE-003
- [ ] QA E2E + verificación visual autenticada de frontend-admin (requiere login super-admin en dev)

---

## Hecho recientemente (reconciliación)

- [x] Suite de aislamiento entre tenants (`pytest -k aislamiento`, 8 verdes) — 2026-07-02
- [x] Pantalla de cumplimiento SAT 69-B en frontend-acceso (`Cumplimiento.tsx`) — ya existía
- [x] Frontend-admin completo (dashboard, detalle+billing, planes CRUD, MFA+QR, créditos, plan, gracia)
- [x] Rate limiting verificado en runtime (11º login → 429) — 2026-07-03

---

## Deuda menor / bugs conocidos

- [ ] `Eventos.tsx`: "Fecha del evento" y "Vigencia desde" comparten `form.vigencia_inicio`
- [ ] Estado "advertencia" del escáner nunca se dispara (backend no setea `data.nota`)
- [ ] `PROMPT_CLAUDE_DESIGN_SAR.md` — referenciado en docs pero nunca creado
- [ ] Adjunto WhatsApp por URL pública → requiere `MEDIA_PUBLIC_BASE_URL` en prod

---

## Diferido — fuera de alcance por ahora (revisar después)

- [~] **Facturación CFDI al cliente por su suscripción** — decidir si lo emite **XentyFiscal** (suite)
      o cada producto el suyo. Fuera de alcance *de momento*.
- [~] **Panel de estado / status page público** — fuera de alcance *de momento*.

---

## Descartado / fuera de alcance

- [~] **ETL MySQL→Postgres + migración de tenants** — el sistema original solo tuvo datos de prueba;
      no hay nada real que migrar. `backend/etl/` y `MIGRACION_DATOS_SAR.md` quedan como referencia.
      Este build es la implementación final (go-live con tenants nuevos vía onboarding).
