# Tareas — Xenty Acceso

> Actualizado: 2026-07-02

## Alta prioridad

- [ ] Verificar foto empleado end-to-end (fix ValueError aplicado, confirmar flujo completo)
  Estado: pendiente
  Contexto: ISSUE-003, fix en config/services.py + Empleados.tsx

- [ ] Confirmar Nginx sirve /media/ en dev
  Estado: pendiente
  Contexto: ISSUE-004, fotos/docs podrían no cargar por URL incorrecta

- [x] Tests pytest — suite de aislamiento entre tenants
  Estado: HECHO (2026-07-02)
  Contexto: obligatorio per CLAUDE.md §4. Implementado en `tests/test_aislamiento_tenants.py`
  (8 tests verdes) + fixture `dos_tenants` en `tests/conftest.py`. Corre con `pytest -k aislamiento`.
  Verifica no-fuga de datos por tenant, padrón EFOS global, resultados 69-B por tenant, cache/storage
  segregados y ausencia de tablas de tenant en `public`. Requiere `requirements-dev.txt` en el
  contenedor (ver STATUS.md).

## Media prioridad

- [ ] Cumplimiento SAT 69-B: pantalla en frontend-acceso
  Estado: pendiente
  Contexto: backend completo (`cumplimiento/services.py` importar_efos, `tasks.py` con retry vía
  Celery); falta UI para ver resultados de validación EFOS

- [~] Frontend-admin funcionalidad completa
  Estado: en progreso (2026-07-02)
  Contexto: Login + lista Tenants + **detalle de tenant** (`TenantDetalle.tsx`: acciones ciclo de
  vida + checkout Stripe) HECHO. Falta: gestión de Planes (CRUD, requiere backend `PlanAdminViewSet`),
  otorgar créditos (requiere endpoint), dashboard control-plane, pantalla MFA super-admin

- [ ] Soporte Mesa de Ayuda (Nivel B)
  Estado: pendiente
  Contexto: SaludConfiguracionView existe, falta integración completa

- [ ] Rate limiting verificar en endpoints críticos
  Estado: pendiente
  Contexto: django-ratelimit configurado en settings pero no probado

## Baja prioridad

- [ ] F8 ETL MySQL→Postgres
  Estado: pendiente
  Contexto: solo cuando se apruebe; etl/ directory existe vacío
  Depende de: aprobación explícita

- [ ] WebAuthn MFA
  Estado: pendiente
  Contexto: TOTP funciona; WebAuthn es complementario

- [ ] Stripe billing integration
  Estado: pendiente
  Contexto: frontend-admin + control plane; Stripe SDK en requirements

- [ ] CI/CD pipeline
  Estado: pendiente
  Contexto: sin GitHub Actions ni similar configurado

- [ ] PROMPT_CLAUDE_DESIGN_SAR.md
  Estado: pendiente
  Contexto: referenciado en docs pero nunca creado
