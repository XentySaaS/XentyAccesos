# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).
> Actualizado: **2026-07-03**. El anterior está en `handoffs/history/HANDOFF_2026-07-02_c.md`.

## Resumen ejecutivo

Sesión larga y productiva. Xenty Acceso quedó **funcionalmente completo** (F0–F7 + F8 reportes) y con
gran parte del **baseline de suite / hardening** cerrado. Cambios grandes de esta tanda:

1. **Suite de aislamiento entre tenants** (`pytest -k aislamiento`, 8 tests) — cerró el bloqueante.
2. **frontend-admin completo** (control plane): dashboard, detalle de tenant con billing/checkout,
   **créditos**, **asignar plan**, **periodo de gracia**, **Planes CRUD**, **MFA TOTP con QR**.
3. **Hardening**: rate limit en login + `Ratelimited→429`, headers de prod (`check --deploy` limpio),
   **redacción de PII en logs** (structlog filter), **`/media` no expone privados**, **health/readiness**,
   **CI/CD (GitHub Actions) con lint bloqueante**, **Flower** (monitoreo Celery), **doble opt-in de email**,
   **Mesa de Ayuda Nivel B**.
4. **Escáner enriquecido** (paridad con el original + mejora): detalle evento/cita, documentos e
   **historial de accesos** en el veredicto.
5. **UI responsive**: sidebar = **drawer flotante en móvil** (3 paneles) + isotipo SVG al colapsar.
6. **Decisión de alcance**: **NO hay migración de datos** (el original solo tuvo datos de prueba) →
   ETL/cutover descartados; este build es la implementación final.
7. **Arquitectura del respaldo de WhatsApp** (`docs/ARQUITECTURA_CONNECTOR.md`) aprobada; **Fase F-A**
   implementada (seam failover-ready en el principal, aún sin el Connector).

Todo commiteado y **pusheado a `origin/main`** (repo `XentySaaS/XentyAccesos`). `ruff` limpio y
bloqueante; suites verdes.

## Estado por módulo

| Área | Estado | Notas |
|---|---|---|
| F0–F7 backend + 3 SPAs | ✔ | Todas las fases de producto cerradas |
| frontend-admin (control plane) | ✔ | Dashboard, tenants, detalle (plan/billing/checkout/créditos/gracia), Planes CRUD, MFA |
| Cumplimiento 69-B | ✔ | Padrón global + UI + auto-actualización |
| soporte (Mesa de Ayuda Nivel B) | ✔ | Salud config + cliente (probar/enviar, sandbox) + config por tenant + `Soporte.tsx` |
| Seguridad/hardening | ✔ (mayor parte) | Rate limit, PII logs, /media, headers prod, health, aislamiento probado |
| Mensajería / Connector | ⏳ F-A hecho | Seam failover-ready; falta F-B (config UI), F-C (Connector Node), F-D/E |
| Tests | ✔ | `pytest` (aislamiento 8 + router 5 + F0 2) verde; CI bloquea lint+tests+build |
| ETL / migración | ✖ descartado | El original solo tuvo datos de prueba (no hay nada real que migrar) |

## Contexto NO obvio (IMPORTANTE)

1. **Nginx cachea la IP del backend** (sigue vigente): al reiniciar/recrear `backend`, Nginx puede
   quedar con la IP vieja → `/api/` responde **502 o 404** (routea a otro contenedor). **Solución:
   `docker compose restart nginx`** tras reiniciar el backend. *(Fix permanente pendiente: `resolver`
   de Docker + `proxy_pass` por variable en `nginx.conf` — propuesto, no aplicado.)*
2. **`ruff` es bloqueante en CI** y el backend está formateado. Config ignora `E501` (lo maneja el
   formatter) y `B904` (diferido). Correr local: `docker compose exec backend ruff check .`
3. **Tests**: la imagen no trae dev-deps. `docker compose exec backend pip install -r requirements-dev.txt`
   y luego `python -m pytest`. La suite crea schemas de tenant (lenta, ~2–3 min).
4. **Email**: `.env` usa **SMTP real de Gmail**. Para pruebas apuntar a Mailpit (`EMAIL_HOST=mailpit`,
   `EMAIL_PORT=1025`, SSL/TLS false). El **doble opt-in** manda correo real en signup con Gmail.
5. **SECURE_SSL_REDIRECT** está gateado por env: prod=True; el `superadmin-backend` en dev lo pone
   `False` (compose) porque corre HTTP. No revertir.
6. **Connector (XCC)**: respaldo de WhatsApp = **repo separado** Node+Baileys (F-C), opcional. El
   principal ya tiene el seam (`apps/mensajeria/{proveedores,breaker,router}.py`). Para sumar un
   proveedor: implementar `ProveedorMensajeria` y registrarlo en `router.proveedores_para`; NO tocar
   el dominio ni `notificar_whatsapp`. Diseño: `docs/ARQUITECTURA_CONNECTOR.md`.
7. **Verificación visual autenticada** del admin/paneles: no realizada por el guard de credenciales
   (no se materializan tokens de super-admin). Todo verificado por tsc/HTTP/shell; el pixel logueado
   lo confirma el usuario.

## Próximos pasos sugeridos

1. **Connector F-B**: config por UI — `ConfiguracionConnector` (global, super-admin) +
   `PreferenciaMensajeria` por tenant (schema del tenant) + pantallas.
2. **Connector F-C**: repo separado Node+Baileys (sesiones/QR/pairing, media completa, REST+HMAC,
   `/healthz`+`/status`, persistencia por tenant). Luego F-D (failover real) y F-E (métricas/webhook/escala).
3. **Deploy a producción**: servir **fotos en prod** (con `DEBUG=False` Django no sirve `/media`),
   Nginx prod + secrets, CI de deploy.
4. **Baseline pendiente**: WebAuthn (opcional), ARCO/LFPDPPP (export+borrado del titular, aviso de
   privacidad), backups/retención, SSO entre productos, notificaciones in-app; reactivar `B904`.
5. **QA responsive por página** (tablas densas → scroll/tarjetas en móvil) + verificación visual E2E.

## Verificar servicios

```bash
docker compose ps                         # todos Up
docker compose restart backend nginx      # tras cambios .py (nginx por el punto #1)
curl -s -o /dev/null -w "%{http_code}" -H "Host: rayados.localhost" http://localhost:8002/health/ready/  # 200
docker compose exec backend pip install -r requirements-dev.txt && docker compose exec backend python -m pytest -q
```
