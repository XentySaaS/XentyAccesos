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
- [ ] **SSO / login unificado entre productos de la suite** (Fiscal / Nómina / Acceso)
- [ ] **Doble opt-in de email** — verificación obligatoria del correo al alta (hoy hay
      `email_verificado` pero falta forzar el flujo de confirmación)
- [x] Roles + permisos granulares (`RequiereRol` / `PermisoUsuario`)
- [x] Rate limiting (login, signup, onboarding, edge, ocr) + `Ratelimited`→429
- [x] Aislamiento multitenant probado (suite `pytest -k aislamiento`)
- [x] Passwords Argon2id · JWT blacklist+rotación · PII cifrada (Fernet)
- [x] Headers de seguridad en prod (`check --deploy` limpio)

### Observabilidad y operación
- [x] Sentry con scrubbing de PII (`before_send`) en prod
- [ ] **Logs estructurados con redacción de PII (structlog cableado)** — el processor
      `common/observability.procesador_structlog` existe pero **no está conectado** a `LOGGING`
- [x] **Health / readiness endpoint** — HECHO (2026-07-03): `GET /health/` (liveness) y
      `GET /health/ready/` (DB+Redis) en `common/health.py`, en ambos planos + ruteado por nginx
- [x] **Monitoreo de Celery** — HECHO (2026-07-03): Flower (`flower` en compose, :5555). Prod: proteger con `--basic-auth`
- [ ] **Notificaciones in-app / centro de notificaciones** (además de email/WhatsApp)
- [x] Versionado de releases (`Version` model + `docs/CHANGELOG.md`)

### Cumplimiento y datos (LFPDPPP / privacidad)
- [x] PII cifrada en reposo + archivos en disco privado por schema
- [ ] **Derechos ARCO / portabilidad**: exportar y **borrar** datos del titular a solicitud
- [ ] **Aviso de privacidad + Términos y condiciones** (legal, aceptación en onboarding)
- [ ] **Backups y política de retención** (respaldo por schema + restauración probada)

### Entrega
- [x] **CI/CD pipeline** — HECHO (2026-07-03): `.github/workflows/ci.yml` (backend pytest + frontend
      build de las 4 SPAs). `ruff` advisory hasta limpiar los 348 hallazgos (ver abajo)
- [ ] **Limpiar lint (ruff)** — 348 hallazgos (E501, orden de imports); luego hacer `ruff` bloqueante en CI
- [ ] Deploy a producción (Nginx prod, secrets por entorno, `DEBUG=False`)
- [ ] `requirements-dev.txt` reproducible en la imagen (hoy `pytest` se instala a mano)

---

## Cierre para producción (específico de Acceso)

- [x] Terminar hardening de logs y `/media` — HECHO (2026-07-03): redacción PII en logs (`RedaccionPIIFilter`
      cableado en `LOGGING`) + `/media` en dev ya no expone privados (INE/REPSE/SUA/docs bloqueados;
      privados por endpoint autenticado con ownership). ISSUE-004 cerrado en su parte de seguridad.
- [ ] Serving de fotos en **producción** (deploy): con `DEBUG=False` Django no sirve `/media`;
      definir cómo se sirven las fotos en prod (nginx desde disco por schema, o endpoint autenticado)
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
