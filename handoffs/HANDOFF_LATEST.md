# Handoff — Xenty Acceso

> **Lee primero:** `CLAUDE.md` (reglas operativas) → este archivo (estado actual).
> Actualizado: **2026-07-08** (3ª tanda del día). El anterior está en
> `handoffs/history/HANDOFF_2026-07-08_b.md` (ARCO/LFPDPPP + onboarding + WebAuthn).

## Resumen ejecutivo

Sesión de **puesta en marcha del entorno local en una máquina nueva** (`C:\Users\ADMIN\Documents\
ProyectosElevation\XentyAccesos`, Windows) + diagnóstico y **fix de tres bloqueos** que impedían usar
el producto de punta a punta:

1. **Entorno levantado desde cero**: no existía `.env` → contenedores no arrancaban. Se generó `.env`
   desde `.env.example` con secretos reales de dev, y se levantó todo el stack (13 servicios).
2. **Super-admin y alta de tenants daban 404** → el control plane no permitía los subdominios
   (`ALLOWED_HOSTS`). Además **no había ningún super-admin sembrado**.
3. **El tenant no cargaba módulos** (solo "Inicio" y "Seguridad") → el admin del tenant tenía el
   **email sin verificar**, y el correo de verificación **nunca se enviaba** porque el control plane
   no tenía backend de correo configurado. Se corrigió la config de email (código) y se puso SMTP de
   Gmail real (`.env`).

**Ningún cambio commiteado aún** (ver §Próximos pasos). Hay 2 archivos de código modificados
(`base.py`, `dev.py`) que sí son fix reales y conviene commitear; el resto son cambios locales de
entorno (`.env`, no versionado).

## Cómo se levanta el entorno (máquina nueva) — PASO A PASO

> Reproduce esto en cualquier máquina limpia con Docker Desktop ya iniciado.

1. **Crear `.env`** (no existe en el repo; es obligatorio o `docker compose` falla con
   `env file .env not found`). Copiar `.env.example` → `.env` y rellenar:
   - `SECRET_KEY` y `SECRET_KEY_FERNET`: **secretos reales, distintos entre sí y sin default**.
     - No hay Python en el host de esta máquina → generados con PowerShell:
       ```powershell
       $b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
       [Convert]::ToBase64String($b).Replace('+','-').Replace('/','_')   # Fernet (32 bytes url-safe)
       ```
       (`SECRET_KEY` = otro token url-safe de 50 bytes.)
   - `ALLOWED_HOSTS=localhost,127.0.0.1,.localhost` ← **el `.localhost` es clave** (ver §Contexto NO
     obvio #1). El `.env.example` NO lo trae; hay que añadirlo.
   - Email: **SMTP de Gmail real** ya configurado en este `.env` (ver §Contexto NO obvio #2).
2. **Verificar que `.env` esté ignorado**: `git check-ignore .env` → debe imprimir `.env`.
3. **Levantar**: `docker compose up -d` (la 1ª vez descarga imágenes y construye; ~varios min).
4. **Sembrar el super-admin** (la tabla `tenants_superadmin` arranca vacía; sin esto no hay login):
   ```bash
   docker compose exec superadmin-backend python manage.py crear_superadmin \
     --email admin@xenty.mx --nombre "Super Admin" --password "<define-una-en-dev>"
   ```
   (Solo permite **uno**; si ya existe, avisa y no crea otro.)
5. **Esperar** ~60-90s a que el backend termine migraciones + provisioning del tenant público
   (health 000/404 mientras tanto; es normal).

### Puertos / servicios (13 contenedores)
| Servicio | Puerto host | Notas |
|---|---|---|
| backend (data plane) | 8002 | settings `dev` |
| superadmin-backend (control plane) | 8003 | settings `control_plane`→`prod` |
| nginx | 8080 | front del navegador; proxya `/api` |
| postgres | 5434 | (interno 5432) |
| redis | 6381 | (interno 6379) |
| mailpit | 1025 SMTP / 8025 UI | **ya NO se usa** (email real por Gmail) |
| celery-worker / beat / flower | 5555 (flower) | |
| frontend-landing / acceso / proveedores / admin | 5173 / 5174 / 5175 / 5176 | Vite dev |

Health: `GET /health/` (raíz, **no** `/api/health/`). Readiness: `/health/ready/`.

## Estado por módulo

| Área | Estado | Notas |
|---|---|---|
| Entorno local (Docker) | ✔ Levantado | 13 servicios Up; público provisionado |
| Login super-admin | ✔ | `admin@xenty.mx` (contraseña de dev definida al sembrar; no se versiona) |
| Alta self-service de tenants | ✔ | signup 201; envía verificación por correo real |
| Verificación de email | ✔ (arreglada) | Ahora el correo sale de verdad (Gmail) |
| Envío SMTP | ✔ | Gmail `smtp.gmail.com:587` STARTTLS — probado, `send_mail -> 1` |
| Producto F0–F8 + 3 SPAs | ✔ | Completo (de sesiones previas) |
| ARCO/LFPDPPP · MFA · WebAuthn · Connector | ✔ | Ver `history/HANDOFF_2026-07-08_b.md` |

## Cambios de esta sesión

### Código (versionado — CONVIENE COMMITEAR)
- **`backend/config/settings/base.py`**: se añadió el bloque **Email (transaccional)** env-driven
  (`EMAIL_BACKEND/HOST/PORT/USE_TLS/USE_SSL/HOST_USER/HOST_PASSWORD/DEFAULT_FROM_EMAIL`). Antes la
  config de correo solo vivía en `dev.py`, pero **el signup corre en el control plane** (que usa
  `prod`, no `dev`) → sin backend de correo → usaba el SMTP default (`localhost:25`) →
  `Connection refused` → correo perdido en silencio.
- **`backend/config/settings/dev.py`**: se **eliminó** el bloque de email duplicado (que además
  tenía el bug `EMAIL_USE_SSL=True`, incompatible con SMTP plano/STARTTLS). Ahora hereda de `base`.

  Commit sugerido: `fix(email): configurar SMTP en base.py para que el control plane envíe verificación`

### Entorno (NO versionado)
- **`.env`** creado. Claves reales de dev + `ALLOWED_HOSTS` con `.localhost` + **SMTP Gmail real**.
- Super-admin sembrado (`admin@xenty.mx`).
- Se marcó `email_verificado` (a mano, dev) del admin del tenant `museos` para desbloquearlo.

### Datos de prueba
- Tenant **`museos`** (`museos.localhost`), admin `manuel@elevation.com.mx`, rol `administrador`,
  email ya verificado. Es el único tenant no-público. (Tenants `demo1` creados para pruebas ya
  fueron eliminados con `Tenant.delete(force_drop=True)`.)

## Credenciales (DEV — no son secretos de prod)

- **Super-admin control plane**: `admin@xenty.mx` en `admin.localhost:8080`. La contraseña se
  definió con `crear_superadmin --password ...` al sembrar; **no se versiona**. Si se pierde, borrar
  la fila de `tenants_superadmin` y volver a sembrar.
- **SMTP Gmail**: `infofin2025@gmail.com`, app password en `.env` (`EMAIL_HOST_PASSWORD`). Si se
  filtra, **revocar en Google** y regenerar. Nunca pegar en archivos versionados.

## Contexto NO obvio (IMPORTANTE)

1. **`ALLOWED_HOSTS` debe incluir `.localhost`** (el punto inicial cubre `localhost` y **todos** sus
   subdominios). El control plane (`superadmin-backend` = `control_plane`→`prod`→`base`) hereda
   `ALLOWED_HOSTS` del `.env`; el data plane (`dev`) usa `["*"]` y por eso no sufría el problema.
   Con solo `localhost,127.0.0.1`, cualquier request a `admin.localhost`/`xenty.localhost`/
   `<tenant>.localhost` en el control plane → host rechazado → django-tenants lo devuelve como
   **404** (no 400). Síntoma: login super-admin y signup daban 404 y el SPA mostraba
   "correo/contraseña incorrectos" o "no se pudo crear la cuenta".
2. **Correo real por Gmail (ya NO Mailpit)**: puerto 587 = **STARTTLS** → en Django es
   `EMAIL_USE_TLS=True` + `EMAIL_USE_SSL=False` (el `SMTPAutoTLS` de PHPMailer no aplica). El
   app password de Gmail se guarda **sin espacios**. `DEFAULT_FROM_EMAIL` = misma cuenta autenticada
   (Gmail reescribe el `From` de todos modos). Para volver a Mailpit en dev: en `.env`
   `EMAIL_HOST=mailpit`, `EMAIL_PORT=1025`, `EMAIL_USE_TLS=False`.
3. **La verificación de email gatea TODO el tenant**: el permiso por defecto
   `common.permissions.EmailVerificado` devuelve **403** en todos los endpoints DRF mientras
   `Usuario.email_verificado` sea `NULL`. El SPA `frontend-acceso` hace
   `api.get("/api/auth/me/").catch(()=>{})`: si `me` falla, el rol queda `""` y el menú
   ([`Layout.tsx`](../frontend-acceso/src/components/Layout.tsx)) solo muestra los ítems sin `roles`
   → **"Inicio" y "Seguridad"**. Por eso "no cargaban los módulos". Fix definitivo del usuario:
   verificar el correo (ahora el enlace llega de verdad).
4. **Rutas por plano**:
   - Control plane (8003, `urls_public`): `POST /api/admin/login/`, `POST /api/signup/`,
     `/api/admin/me/`, MFA admin.
   - Data plane (8002, `urls`): `POST /api/auth/acceso/login/` (Usuario),
     `POST /api/auth/proveedores/login/` (CuentaProveedor), `/api/auth/me/`, MFA tenant.
   - Campos de signup: `nombre`, `subdominio`, `admin_nombre`, `admin_email`, `admin_password`.
5. **Las env se cargan al CREAR el contenedor, no al `restart`**: tras tocar `.env` hay que
   `docker compose up -d --force-recreate <servicios>`. Tras tocar solo `.py` (van por volumen
   montado) basta `docker compose restart backend superadmin-backend nginx`.
6. **Sin Python en el host** de esta máquina: todo se ejecuta dentro de contenedores
   (`docker compose exec ...`). Para el shell de Django usar `manage.py shell -c "..."` (un
   `python -c` suelto falla con `DJANGO_SETTINGS_MODULE` no configurado).
7. **Borrar un tenant** en dev: `Tenant.objects.get(schema_name=...).delete(force_drop=True)` (hace
   DROP SCHEMA). Vía `manage.py shell` en cualquiera de los dos backends.

## Próximos pasos sugeridos

1. **Commitear el fix de email** (`base.py` + `dev.py`). No commitear `.env`.
2. **QA end-to-end de onboarding** con un correo real: crear tenant desde la UI
   (`xenty.localhost:8080`), recibir el enlace de verificación en el buzón, confirmarlo, y comprobar
   que el SPA del tenant ya carga todos los módulos.
3. **Brecha de UX (no bloqueante)**: cuando `/api/auth/me/` da 403 por email no verificado, el SPA
   muestra un menú vacío en vez de un aviso "verifica tu correo". Manejar ese 403 con una pantalla
   dedicada.
4. **Baseline #2 restante** (del handoff anterior): backups/retención, SSO suite, notificaciones
   in-app, reactivar `B904` en ruff. **Connector F-E** + crear repo remoto. **MFA de CuentaProveedor**.
5. **`.env.example`**: considerar documentar `ALLOWED_HOSTS=...,.localhost` y las vars de email
   (`EMAIL_USE_TLS/SSL`, `EMAIL_HOST_USER/PASSWORD`, `DEFAULT_FROM_EMAIL`) para que la próxima
   máquina no repita el diagnóstico. (Sin valores reales, solo placeholders.)

## Verificar servicios

```bash
docker compose ps                                    # los 13 Up
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: localhost" http://localhost:8002/health/   # 200
# login super-admin (subdominio):
curl -s -X POST -H "Host: admin.localhost" -H "Content-Type: application/json" \
  -d '{"email":"admin@xenty.mx","password":"<tu-contraseña-dev>"}' http://localhost:8003/api/admin/login/
# prueba SMTP (envía correo real a la propia cuenta):
docker compose exec superadmin-backend python manage.py shell -c \
  "from django.core.mail import send_mail; from django.conf import settings; \
   print(send_mail('Prueba','ok',settings.DEFAULT_FROM_EMAIL,['infofin2025@gmail.com']))"
docker compose restart backend superadmin-backend nginx    # tras cambios .py
docker compose up -d --force-recreate backend superadmin-backend celery-worker celery-beat  # tras .env
```
