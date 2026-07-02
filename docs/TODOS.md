# Tareas — Xenty Acceso

> Actualizado: 2026-07-02

## Alta prioridad

- [ ] Verificar foto empleado end-to-end (fix ValueError aplicado, confirmar flujo completo)
  Estado: pendiente
  Contexto: ISSUE-003, fix en config/services.py + Empleados.tsx

- [ ] Confirmar Nginx sirve /media/ en dev
  Estado: pendiente
  Contexto: ISSUE-004, fotos/docs podrían no cargar por URL incorrecta

- [ ] Tests pytest — suite de aislamiento entre tenants
  Estado: pendiente
  Contexto: obligatorio per CLAUDE.md §4; existe `tests/test_f0_modelos.py` (58 líneas) pero falta
  la suite `-k aislamiento` que verifique que datos de un tenant no filtran a otro

## Media prioridad

- [ ] Cumplimiento SAT 69-B: pantalla en frontend-acceso
  Estado: pendiente
  Contexto: backend completo (`cumplimiento/services.py` importar_efos, `tasks.py` con retry vía
  Celery); falta UI para ver resultados de validación EFOS

- [ ] Frontend-admin funcionalidad completa
  Estado: pendiente
  Contexto: actualmente solo Login + Tenants (lista); falta CRUD tenants, planes, billing Stripe

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
