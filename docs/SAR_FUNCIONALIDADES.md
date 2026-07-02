# SAR_FUNCIONALIDADES — Catálogo funcional (Xenty Acceso)

> Especificación de **qué debe hacer** el sistema, módulo por módulo: funcionalidades, máquinas de
> estado, reglas de negocio, permisos por rol y flujos. Es la referencia de **paridad funcional**
> para la reconstrucción: el comportamiento se preserva aunque el código y el esquema se rehagan.
>
> Derivado del análisis del sistema origen (Laravel/Filament). Donde la reconstrucción **cambia**
> una conducta (seguridad o limpieza), se marca con ⟳. Modelos en `MODELO_DATOS_SAR.md`; el orden de
> implementación en `PLAYBOOK_SAR_XENTY.md`.

---

## 1. Actores y roles

| Contexto | Modelo | Roles | Acceso |
|---|---|---|---|
| Control plane | SuperAdmin | super-admin | Tenants, planes, billing, dispositivos edge |
| Tenant — operación | `Usuario` | Administrador, Editor, Guardia, Gerente, Recepcionista, Usuario, Verificador | SPA `acceso` |
| Tenant — autoservicio | `CuentaProveedor` | Admin, Usuario | SPA `proveedores` (solo su empresa) |

Permisos: rol primario (campo `rol`) evaluado por `RequiereRol`; módulos comerciales por
`RequiereModulo` (HTTP 402). ⟳ Sin IDs de rol hardcodeados (el origen ataba 1..6 a IDs de Spatie).

---

## 2. Módulo Recintos (topología física) · F1

CRUD de la topología que contextualiza eventos, citas y accesos.

- **Recinto** (`code` único): nombre, descripción, teléfono.
- **Zona** → Recinto (cascade); nombre único **por recinto** ⟳ (origen: único global).
- **Acceso** → Recinto (cascade); nombre único por recinto ⟳.
- **Ubicación** → Zona; jerarquía con `padre` (FK self real ⟳).
- **Entrada** → Acceso; jerarquía con `padre` (FK self real ⟳).
- **Área autorizada** → Recinto; estado activo/inactivo; se asocia a eventos, citas y evento-proveedor.
- **Protocolo**: PDF ≤10MB ⟳ (validación MIME/tamaño), estado activo/inactivo.

Permisos: Administrador. Auditoría: alta/edición/baja registran en `HistorialCambio`.

---

## 3. Módulo Proveedores · F1

### 3.1 Catálogo y onboarding

- **Proveedor** (empresa externa): nombre, razón social, RFC, email/teléfono/dirección, responsable
  (FK a `CuentaProveedor`), archivos REPSE/SUA. Email del responsable **único**.
- **Cuenta de proveedor** (`CuentaProveedor`): credenciales del panel proveedor; CURP/NSS cifrados ⟳;
  INE en disco privado ⟳.
- **Validación de RFC**: estructura + dígito verificador al registrar.

### 3.2 Máquina de estados del proveedor

```
pendiente ──(abre invitación válida)──> confirmado ──(admin aprueba docs)──> activo ──> inactivo (baja)
```
- **Invitación**: token **firmado** con vigencia 72h ⟳ (origen: AES-ECB con clave en git).
- **Reenvío** de invitación visible solo si `estado=pendiente` y `updated_at > 3 días`.
- Subida de archivos del onboarding con validación MIME/tamaño ⟳; nombre lo asigna el servidor.

Permisos: Administrador (alta, aprobación, revisión de docs).

---

## 4. Módulo Empleados · F1

Plantilla del proveedor (panel `proveedores`, filtrada por su empresa).

- **Empleado** → CuentaProveedor (cascade): nombre, email (no único ⟳, el origen quitó el unique),
  teléfono, foto (captura por cámara), estado activo/inactivo/**baja**.
- **Import Excel**: `firstOrNew` por email (idempotente).
- ⟳ **Baja lógica**: `estado=baja` congela; nunca se borra físicamente.

Permisos: Admin/Usuario del proveedor (solo sus empleados).

---

## 5. Módulo Documentos y validación documental · F2

### 5.1 Catálogo

- **Grupo de documentos** (estado activo/inactivo).
- **Tipo de documento** → Grupo (FK nullable).
- Asociación a evento: **grupo↔evento** con `type_validation` (0 = al menos uno / 1 = todos) y
  **tipo↔evento**.

### 5.2 Documento de empleado

```
PENDIENTE (0) ──[Verificar]──> VERIFICADO (1)  → recalcula checkdocs
              ──[Rechazar]───> RECHAZADO (2)   → email al proveedor
```
- Subida (PDF/JPG/PNG ≤2MB ⟳ validado) a disco privado por schema ⟳; alta notifica a verificadores/admins.
- ⟳ Estado como entero 0/1/2 (el origen tenía drift boolean/int).

### 5.3 Regla `checkdocs` (central)

Para cada evento del empleado, por cada grupo requerido del evento:
- `type_validation = 0` → basta **un** documento del grupo en estado VERIFICADO.
- `type_validation = 1` → **todos** los documentos del grupo deben estar VERIFICADOS.

Si **todos** los grupos cumplen → `EmpleadoEventoProveedor.statusdocs = CUMPLE`. El empleado solo
puede ingresar con `statusdocs=CUMPLE`.

Permisos: Administrador y Verificador (este último filtrado a **sus** eventos asignados).

---

## 6. Módulo Eventos · F3

### 6.1 Evento

```
programado → en_curso → completado          (transiciones manuales)
     └──────── cancelado (acción "Cancelar") ── dispara WhatsApp a todos los proveedores
```
Reglas:
- `vigencia_fin >= vigencia_inicio` (si no, se rechaza con error).
- **No eliminable** si tiene proveedores o empleados asignados.
- "Cancelar" oculto si ya está `cancelado` o `completado`.
- Usuario **no** Administrador solo ve los eventos que él creó.
- Verificadores del evento (M2M con `Usuario`).
- Grupos/tipos de documento requeridos; áreas autorizadas.

### 6.2 Evento-Proveedor (invitación a un evento)

- Define para el proveedor en ese evento: zona, acceso, ubicación, punto de acceso, protocolo,
  `limite` de personas, parking (`requiere_parking`, `cajones_parking`), notas.
- **Cajón de parking**: cada cajón es un `CajonParking.uuid` (va dentro del QR de estacionamiento).

### 6.3 Asignación masiva (lado proveedor)

1. Valida no exceder `limite` de personas del evento-proveedor.
2. Solo permite empleados con los documentos requeridos **verificados** (`checkdocs`).
3. Sincroniza el pivote con `statusdocs` y dispara emisión de gafete QR (WhatsApp + email).

Permisos: Administrador/Editor (operación); Admin/Usuario proveedor (asignación masiva de su plantilla).

---

## 7. Módulo Citas · F4

### 7.1 Tipos y estados

- **Tipo proveedor** (`tipo=0`): requiere `proveedor` y `limite`; notifica al responsable (email + WhatsApp).
- **Tipo directa** (`tipo=1`): lista de invitados; busca/crea `Contacto` si no existe; dispara emisión.
- **Tipo de cita**: programada / **walk-in** / emergencia. ⟳ En walk-in, el flujo crea el
  `RegistroAcceso` de entrada automáticamente.
- **Estado**: pendiente → confirmada → cancelada.
- **Cascada obligatoria** de selección: Recinto → Zona → Ubicación → Acceso.
- **No eliminable** si (tipo=0 con empleados) o (tipo=1 con asistentes).

### 7.2 Asistente de cita

- Datos del invitado; `persona` polimórfica (Contacto o Empleado) ⟳ resuelta con GenericForeignKey.
- Estado pendiente/confirmado/cancelado.

### 7.3 OCR de INE (asistentes)

- Si `requiere_ine`, se captura la INE → AWS Textract → parseo de campos (nombre, domicilio, CURP,
  sexo, fecha de nacimiento, sección…) con validadores.
- ⟳ Eliminar la validación hueca `validaSeccionINE` (que siempre devolvía true): implementarla de
  verdad o quitar el campo.
- ⟳ `ine_data` cifrado (Fernet); imagen INE en disco privado.

Permisos: Administrador, Editor, Recepcionista, Guardia (según el origen para citas).

---

## 8. Módulo Gafetes y QR · F5

- Emisión de **gafete PNG** con QR para evento, cita o parking.
- ⟳ QR **firmado/cifrado** (Fernet o HMAC) con payload `id|contexto|tipo` (01 evento, 02 parking,
  03 cita) + `jti` único + vigencia. Reemplaza el AES-ECB con clave en código del origen.
- Reenvío por WhatsApp + email al asignar/confirmar.
- ⟳ Sin endpoint público de emisión de prueba (el origen tenía `/test`).

---

## 9. Módulo Acceso físico · F5

### 9.1 Validación al escanear (guardia web o dispositivo edge)

Al leer un QR (`POST /api/acceso/escanear/`), primero se revisa si ya existe una entrada del día
sin salida para ese mismo portador (empleado/asistente/cajón): si existe, el escaneo **alterna a
salida** (`hora_salida = now()`) sin re-evaluar las reglas de negocio — salir nunca se bloquea.
Si no hay entrada abierta, se evalúa según el tipo de QR:

- **Evento** (`EmpleadoEventoProveedor`): vigencia del evento (`vigencia_inicio ≤ hoy ≤
  vigencia_fin`), `statusdocs = CUMPLE`, sin sanción activa (`Sancion` BAJA o SUSPENSION vigente).
- **Cita** (`AsistenteCita`): `Cita.estado ≠ CANCELADA`, `AsistenteCita.estado ≠ CANCELADO`, y
  `Cita.fecha == hoy` (la cita es de un solo día, sin rango de vigencia).
- **Parking** (`CajonParking`): vigencia del evento padre (mismo rango que evento).

La respuesta incluye `nombre`/`empresa`/`foto_url` del portador (cuando aplica) para que el
guardia coteje visualmente contra la persona frente a él — obligatorio en QR forjados o prestados.
Se registra `RegistroAcceso` (o `RegistroAccesoParking`): `tipo_acceso = entrada | denegado`;
`metodo = qr | placa | manual | tarjeta`.

### 9.2 Override del guardia, salida y parking

- **Rechazo manual**: `POST /api/acceso/registros/{id}/rechazar/` — el guardia puede convertir una
  entrada recién concedida en denegada (con motivo obligatorio) cuando la foto no coincide con
  quien porta el QR. Solo aplica a una entrada del propio escaneo, sin salida registrada aún; no
  se puede rechazar dos veces ni revertir una salida.
- **Salida manual**: acción "Registrar salida" en la Bitácora → `hora_salida = now()` + WhatsApp de
  confirmación (pendiente de conectar, ver F7).
- **Parking**: el escáner de parking valida el `CajonParking.uuid` y registra `RegistroAccesoParking`
  con número de personas y placa; alterna entrada/salida igual que evento/cita.

Permisos: Guardia (escáner + rechazo). Bitácora y reportes: Administrador.

---

## 10. Módulo Sanciones · F5

- **Sanción** sobre un empleado, en contexto de evento o cita.
- `severidad` (Bajo/Medio/Alto) y `penalidad` (Advertencia/Suspensión/Baja) **solo editables por
  Administrador**.
- **Suspensión** exige `fecha_inicio` y `fecha_fin`.
- Sanción activa bloquea el acceso (§9.1.5).

---

## 11. Módulo Dispositivos edge · F6

Dispositivos Raspberry Pi en torniquetes/plumas (gestionados desde el control plane).

- **API HMAC** (`/api/v1/*`): firma sobre `MÉTODO-RUTA-TIMESTAMP` con token por dispositivo,
  `compare_digest`, ventana de tiempo + **nonce anti-replay** ⟳.
- **Validación de QR** desde el dispositivo, **dentro del tenant del dispositivo** ⟳ (corrige fuga
  cross-tenant) y registro de acceso.
- **Comandos** (long-poll): el panel crea `ComandoEdge` (`relay.open`, `display.text`, `pending`);
  el dispositivo hace `pull` (→`sent`) y `ack` (→`ack`). ⟳ Filtro por dispositivo correcto
  (corrige el bug que permitía `ack` de comandos ajenos).

---

## 12. Módulo Mensajería (WhatsApp) · F7

- **Campaña** segmentada por recinto / zona / evento / todos los eventos / todos los recintos /
  recintos y zonas.
- **Estados** de la campaña: pendiente → en progreso → (cancelado) / completado; `progreso` por
  destinatario.
- **Destinatario**: estado pendiente/enviado/fallido, `external_id` (id de UltraMsg). ⟳ Índice en
  estado para seguimiento.
- ⟳ Credenciales de WhatsApp desde entorno (el origen las tenía hardcodeadas); cliente tras interfaz.
- Envío vía Celery con reintentos por tarea ⟳ (el origen usaba `dispatchAfterResponse` sin reintentos).

Permisos: Administrador.

---

## 13. Módulo Cumplimiento SAT 69-B · F7

- **Espejo del CSV oficial** SAT 69-B (EFOS) en `SatEfo` (RFC indexado/único, situación, meta).
- **Frecuencia** configurable (default mensual); `--force` ignora el límite; el importador corre por
  Celery beat ⟳ (el origen no tenía scheduling configurado).
- **Estatus bloqueantes** configurables: `Definitivo`, `Presunto`.
- **Validación**: el RFC del proveedor se valida contra EFOS al registrarse y en corridas
  programadas; resultados en `ResultadoLista69b` (`query_data` JSON), consultables en una página y
  un widget de dashboard.

Permisos: Administrador.

---

## 14. Usuarios, auditoría y configuración

### 14.1 Usuarios del tenant (operación) · F0/F1
- Roles: Administrador, Editor, Guardia, Gerente, Recepcionista, Usuario, Verificador.
- Login exige `activo=True`.
- ⟳ "Eliminar" usuario = baja lógica (`activo=False` + `fecha_baja`); usuarios Administrador no se
  eliminan.
- Reset de contraseña con rate-limit ⟳.

### 14.2 Auditoría (HistorialCambio) · F8
- Bitácora append-only: descripción, modelo, modelo_id, usuario, acción
  (creado/actualizado/eliminado/restaurado/asignado/desasignado/visto/listado).
- ⟳ Paginada (el origen traía todo sin paginar) e indexada por usuario y (modelo, modelo_id).
- Decisión abierta: registrar diff antes/después (campos listos pero vacíos).

### 14.3 Configuración (Opcion) · F0
- Clave-valor para ajustes del tenant (logo, fondos…), reemplaza el helper `get_option()`.

### 14.4 Dashboard / calendario / reportes · F8
- Dashboard: KPIs (invitados vs ingresados por recinto, eventos actuales).
- Calendario mensual de eventos + citas.
- Reportes de acceso exportables a Excel.

---

## 15. Tabla resumen de reglas críticas (verificables en tests)

| Regla | Módulo | Esperado |
|---|---|---|
| `checkdocs` con `type_validation 0/1` | Documentos | 0 = al menos uno verificado; 1 = todos verificados → `statusdocs=CUMPLE` |
| Asignación masiva | Eventos | respeta `limite`; exige docs verificados |
| Evento no eliminable | Eventos | bloqueado si hay proveedores/empleados |
| `vigencia_fin >= vigencia_inicio` | Eventos | rechazo si no se cumple |
| Cancelar evento | Eventos | dispara WhatsApp a proveedores |
| Invitación proveedor | Proveedores | token firmado, vigencia 72h, reenvío >3 días |
| Walk-in | Citas | crea RegistroAcceso de entrada automático |
| Cascada de selección | Citas | Recinto→Zona→Ubicación→Acceso obligatoria |
| Validación de acceso | Acceso | pertenencia + vigencia + `statusdocs` + sin sanción |
| QR inviolable | Gafetes/Acceso | payload manipulado o expirado → rechazo |
| Suspensión | Sanciones | exige fecha_inicio y fecha_fin; bloquea acceso |
| 69-B | Cumplimiento | estatus Definitivo/Presunto bloquean; validación por RFC |
| Anti-replay edge | Dispositivos | nonce reutilizado → rechazo |
| Aislamiento edge | Dispositivos | QR de otro tenant → rechazo, sin fuga |

---

*Fin del catálogo funcional. Último documento de la suite: `PROMPT_CLAUDE_DESIGN_SAR.md` (brief de UI
para las tres SPAs).*
