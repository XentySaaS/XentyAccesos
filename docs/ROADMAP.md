# Roadmap — Xenty Acceso

> Actualizado: 2026-07-02 · Fases según `docs/PLAYBOOK_SAR_XENTY.md` (única numeración válida)

## Fases del playbook

| Fase | Descripción | Estado backend | Estado frontend |
|---|---|---|---|
| F0 | Cimientos: control plane, auth dual, MFA TOTP, Argon2id | ✔ | ✔ (3 shells) |
| F1 | Recintos + Proveedores + Empleados | ✔ | ✔ |
| F2 | Documentos y validación documental (`checkdocs`) | ✔ | ✔ |
| F3 | Eventos | ✔ | ✔ |
| F4 | Citas y OCR de INE | ✔ | ✔ |
| F5 | Gafetes, QR firmado, acceso físico y sanciones | ✔ | ✔ |
| F6 | Dispositivos edge (HMAC + nonce anti-replay + long-poll) | ✔ | — (sin panel; son dispositivos físicos) |
| F7 | Mensajería WhatsApp y cumplimiento SAT 69-B | ✔ | ✔ (Mensajería + Cumplimiento) |
| F8 | Reportes, dashboard, calendario, ETL y hardening final | ⚠ ETL scaffolded | ⚠ Dashboard/calendario/reportes ✔; ETL y hardening pendientes |

> Nota: "roles y permisos granulares" (PermisoUsuario) no es una fase numerada del playbook — es una
> mejora transversal añadida sobre F1 (accounts) en la sesión 2026-07-02.

## Detalle por fase

### F6 — Dispositivos edge (backend completo)

- `EdgeHMACAuthentication`: firma HMAC-SHA256 sobre `METHOD-PATH-TIMESTAMP`, ventana de 300s,
  nonce anti-replay vía Redis (`cache.add`)
- `DispositivoEdge` / `ComandoEdge` viven en `apps.tenants` (control plane, ligados a tenant)
- Archivos: `backend/apps/dispositivos/{authentication,services,views}.py`

### F7 — Mensajería (backend completo) + Cumplimiento (backend completo, sin UI)

**Mensajería:**
- `Mensaje`, `DestinatarioMensaje` models
- `procesar_envio()` — segmentación por evento/recinto, envío vía `UltraMsgWhatsApp` o `SandboxWhatsApp`
- Celery `enviar_campana` con `max_retries=3` — retry queue YA IMPLEMENTADA
- Pantalla en `frontend-acceso/src/pages/Mensajeria.tsx`

**Cumplimiento:**
- `importar_efos()` service + `importar_efos_task` (Celery, retry, descarga CSV de `SAT_EFOS_CSV_URL`)
- **Pendiente:** pantalla en frontend-acceso para ver resultados de validación EFOS

### F8 — Reportes/Dashboard/ETL (scaffolded, no terminado)

**Existe:**
- `DashboardView`, `CalendarioView`, `ExportarAccesosView` en `apps/config/views.py`
- `backend/etl/transformers.py` (63 líneas — transformaciones parciales)
- `manage.py migrar_tenant_sar <subdominio> --dry-run` (64 líneas — comando con flag dry-run)

**Pendiente:**
- Verificar cobertura real del ETL contra `MIGRACION_DATOS_SAR.md` (probablemente incompleto)
- Frontend de reportes/dashboard en frontend-acceso o frontend-admin
- Hardening final (checklist de `REMEDIACION_SEGURIDAD_SAR.md`)

## Funcionalidades transversales pendientes

- ✔ Tests pytest suite `-k aislamiento` — HECHO (2026-07-02): `tests/test_aislamiento_tenants.py`
  (8 tests verdes) + `tests/conftest.py`
- WebAuthn MFA (TOTP ya funciona)
- CI/CD pipeline
- Rate limiting: configurado, no verificado en runtime
- Nginx `/media/` en dev: pendiente confirmar

## Prioridad actual

1. Pantalla de cumplimiento SAT 69-B (backend ya listo)
2. Auditar cobertura real del ETL F8 contra el modelo de datos origen
3. Frontend-admin funcional (CRUD tenants, billing)
