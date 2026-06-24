# MIGRACION_DATOS_SAR — ETL MySQL → PostgreSQL por tenant

> Plan de migración de los datos productivos del SAR (MySQL, una BD por tenant) al esquema destino
> limpio (PostgreSQL, schema por tenant). Cubre extracción, transformación (renombrados, tipos,
> reconstrucción de FKs, re-cifrado de PII, reemisión de QR) y carga, con validación y cutover.
>
> Depende de `MODELO_DATOS_SAR.md` (esquema destino) y `REMEDIACION_SEGURIDAD_SAR.md` (re-cifrado,
> reemisión). Se ejecuta en **F8** del `PLAYBOOK_SAR_XENTY.md`, una vez que el esquema destino existe.

---

## 1. Inventario de origen

**Bases de datos MySQL** (prefijo `tenant_` confirmado en `config/tenancy.php`):

| BD MySQL | Tipo | Contenido |
|---|---|---|
| BD central | central | `tenants`, `domains`, `devices_tenants`, `edge_commands`, `users`(SaaS) |
| `tenant_<id>` × N | por tenant | ~50 tablas de negocio (una BD por cliente) |

**Tenants productivos conocidos** (evidencia en `temporal/.env.*`): `rayados`, `3museos`, `tyasa`,
`acceso`. El `tenant_id` real es un UUID; el subdominio es el nombre. Confirmar el censo completo
consultando `domains`/`tenants` en la BD central antes de migrar.

**Almacenamiento de archivos** (storage con sufijo `tenant<tenant_id>`): imágenes INE
(`app/public/ine/`), fotos de empleados (`app/public/photos/`), gafetes PNG, documentos (REPSE/SUA,
docs de empleado), protocolos PDF. La muestra en `temporal/tenantdbs15329779/` confirma el layout.

> **Las BD no están en el repo**: el ETL corre contra los MySQL **en producción** (solo lectura) o
> contra dumps recientes. El repo solo trae el storage de muestra y los `.env` (que NO se usan;
> credenciales rotadas, REMEDIACION §1).

---

## 2. Estrategia general

**Pipeline por tenant, idempotente y repetible** (permite ensayos sin efectos):

```
Para cada tenant (empezando por uno piloto, p. ej. el de menor volumen):
  1. EXTRACT  → leer tablas MySQL del tenant (solo lectura) a estructuras intermedias
  2. TRANSFORM→ renombrar, convertir tipos/enums, reconstruir FKs, resolver polimorfismo,
                consolidar drift, re-cifrar PII
  3. LOAD     → CREATE SCHEMA <tenant> + migrate_schemas + insertar dentro de tenant_context
  4. FILES    → copiar archivos a storage privado por schema (INE/fotos/docs/protocolos)
  5. REISSUE  → reemitir QR/gafetes con cifrado nuevo; invalidar los viejos
  6. VALIDATE → conteos, muestras, integridad referencial, aislamiento
  7. (opcional) rollback: DROP SCHEMA <tenant> y reintentar
```

**Herramienta**: management command Django `migrar_tenant_sar <subdominio>` (o Celery task por
tenant), usando SQLAlchemy/`mysql-connector` para leer MySQL y el ORM Django para escribir.
**Orden de carga** respeta dependencias de FK (ver §4). **Mapeo de IDs**: se preservan los `id`
originales cuando es posible (simplifica FKs); si hay colisión con autoincrementales, se mantiene un
diccionario `{tabla: {id_viejo: id_nuevo}}` por tenant.

---

## 3. Control plane (BD central → schema `public`)

| Origen MySQL | Destino | Transformación |
|---|---|---|
| `tenants` | `Tenant` (Xenty) | `subscription_status` (active/inactive/suspended) → estado Xenty (trial/activo/suspendido/cancelado); `trial_ends_at`, `data` JSON se preservan; `company`→nombre. Crear `SaldoCreditos` inicial = 0 |
| `domains` | `Domain` | directo (`domain` → subdominio) |
| `devices_tenants` | `DispositivoEdge` | `token` HMAC → **re-generar** secreto nuevo y re-aprovisionar el dispositivo físico (el viejo estaba en git, comprometido); almacenar cifrado/hash |
| `edge_commands` | `ComandoEdge` | migrar solo `pending` recientes; los históricos `sent/ack` son descartables |
| `users` (SaaS central) | `SuperAdmin` | passwords se **resetean** (hash MySQL no se reusa); invitar a re-establecer |

> Los tokens HMAC de dispositivos y los passwords de super-admin **no se migran tal cual**: se
> regeneran (REMEDIACION §1, C3/C1). Implica coordinación con el aprovisionamiento físico de los Pi.

---

## 4. Data plane (BD tenant → schema por tenant)

Orden de carga por dependencias (cada bloque depende de los anteriores):

```
1. recintos: Recinto → Zona, Acceso → Ubicacion, Entrada → AreaAutorizada; Protocolo
2. identidad: Usuario(users) ; Proveedor(suppliers) → CuentaProveedor(providers) → Empleado(employees)
3. documentos: GrupoDocumentos → TipoDocumento ; (catálogo)
4. eventos: Evento → EventoProveedor → CajonParking ; pivots (Empleado↔EvProv, Verificador↔Evento,
            Evento↔Grupo/Tipo doc, Área↔Evento/EvProv)
5. citas: Contacto ; Cita → AsistenteCita (resolver person_id) ; EmpleadoCita ; Área↔Cita
6. documentos de empleado: DocumentoEmpleado (verified 0/1/2)
7. operación: RegistroAcceso, RegistroAccesoParking ; Sancion
8. comunicación/cumplimiento: Mensaje → DestinatarioMensaje ; SatEfo, ConsultaLista69b, ResultadoLista69b
9. config/auditoría: Opcion ; HistorialCambio
```

### 4.1 Transformaciones por tabla (las no triviales)

| Origen | Destino | Transformación clave |
|---|---|---|
| `users` | `Usuario` | `role` enum→`Rol` (mapa abajo); `low_login`/`delete_at` → `activo`/`fecha_baja`; password **reset** (no se migra hash); descartar `company_id` |
| `providers` | `CuentaProveedor` | `company_id`→FK `proveedor`; `curp`/`nss`→**cifrar**; `file_ine` a disco privado; password **reset** |
| `suppliers` | `Proveedor` | `user_id`→FK `responsable`; `RFC`→`rfc` (uppercase/trim); estado directo |
| `employees` | `Empleado` | `provider_id`→FK; `status` terminated→`baja` |
| `locations`/`entries` | `Ubicacion`/`Entrada` | `parent_id` → FK self real (validar que el padre exista; si 0/huérfano → `null`) |
| `zones`/`accesses` | `Zona`/`Acceso` | `name` unique global → `unique_together(recinto,nombre)`: si hay colisión cross-recinto, deduplicar/renombrar y registrar |
| `events` | `Evento` | `start_time`/`end_time`(date)→`vigencia_inicio`/`vigencia_fin`; `hora_inicio`/`hora_fin`→time; **`date` se compara con `vigencia_inicio`**: si difieren, log y decidir; `status` directo |
| `event_suppliers` | `EventoProveedor` | `zone_id`/`access_id` (alters) presentes; `req_parking`→bool; `parking` text→`notas`/derivar |
| `employee_event_supplier` | `EmpleadoEventoProveedor` | `statusdocs` 0/1 directo |
| `appointments` | `Cita` | `created_by`/`assigned_to` (sin FK)→FK `Usuario` (validar IDs; huérfano→null); `time_start/end`→time |
| `assistent_appointments` | `AsistenteCita` | **`person_id`+`type`** → `GenericForeignKey`: type=0→Contacto, type=1→Empleado (resolver `content_type`+`object_id`); `ine_data`→**cifrar**; `path_ine` a disco privado; `identification_number`→**cifrar** |
| `employee_documents` | `DocumentoEmpleado` | `verified` boolean/0-1-2 → `IntegerChoices` (validar valores reales en datos; mapear true→VERIFICADO, false→PENDIENTE, 2→RECHAZADO) |
| `list_documents` | `TipoDocumento` | `group_documents_id`→FK `grupo` (nullable; huérfano→null); `status` string→bool |
| `messages` | `Mensaje` | `type_id` se conserva como `segmento_id` (ref lógica por `segmento`); `status` 0..3→`Estado` |
| `message_recipients` | `DestinatarioMensaje` | `external_id` bigint→char; `status` directo |
| `result__lista69bs` | `ResultadoLista69b` | `query_data` JSON directo; `lista_69b_id`→FK `consulta` |
| `change_histories` | `HistorialCambio` | `action` enum directo; `antes`/`despues` quedan null (origen no tiene diff) |

### 4.2 Mapas de enum (origen → destino)

```
users.role:        Administrator→administrador, Editor→editor, "Security Guard"→guardia,
                   Manager→gerente, Receptionist→recepcion, User→usuario, Verifier→verificador
providers.role:    Admin→admin, User→usuario
*.status (genérico): active→activo, inactive→inactivo, pending→pendiente, confirmed→confirmado,
                   terminated→baja
events.status:     scheduled→programado, ongoing→en_curso, completed→completado, cancelled→cancelado
appointments.status: pending→pendiente, confirmed→confirmada, cancelled→cancelada
appointment_type:  scheduled→programada, walk-in→walk_in, emergency→emergencia
access_logs.access_type: entry→entrada, denied→denegado ; access_method: QR→qr, etc.
warnings.severity: Bajo→bajo, Medio→medio, Alto→alto ; penalty: Advertencia→advertencia,
                   Suspensión→suspension, Baja→baja
message status (int): 0→pendiente,1→en_progreso,2→cancelado,3→completado (Mensaje)
recipient status: pending→pendiente, sent→enviado, failed→fallido
```

---

## 5. Re-cifrado de PII (durante el TRANSFORM)

Datos que en origen están en claro y al cargar pasan por cifrado Fernet (REMEDIACION §A2):

- `providers.curp`, `providers.nss` → `EncryptedCharField`.
- `assistent_appointments.ine_data` (JSON) → `EncryptedJSONField`.
- `assistent_appointments.identification_number` → `EncryptedCharField`.
- Imágenes INE (`app/public/ine/*`) y `path_ine` → **copiar a disco privado por schema**; ruta
  pública vieja se abandona. Fotos de empleados pueden seguir en disco de media controlado (no PII
  sensible), pero igualmente por schema.

El cifrado lo hace el propio modelo Django al guardar (campos `Encrypted*`), así que el ETL solo
necesita escribir el valor en claro al campo y el ORM lo cifra. **Verificar** post-carga que la BD
contiene ciphertext (no el valor original).

---

## 6. Reemisión de credenciales (QR / gafetes / invitaciones)

Los QR y tokens viejos usan el cifrado comprometido (`EncryptionHerper`, AES-ECB clave en git,
REMEDIACION C3). **No se migran los QR; se reemiten**:

- **Gafetes de evento/cita/parking activos**: tras cargar `EventoProveedor`/`AsistenteCita`/
  `CajonParking`, el servicio `apps.gafetes` re-genera el QR firmado/cifrado nuevo (con `jti`+`exp`)
  y, opcionalmente, reenvía por WhatsApp/email. Los gafetes viejos quedan inválidos al apagar el
  verificador viejo.
- **Tokens de invitación de proveedor** en vuelo (`pending`): se re-emiten con el firmador nuevo;
  los viejos expiran solos a las 72h.
- **Ventana de corte**: coordinar por tenant para minimizar gafetes vigentes en el cambio (idealmente
  fuera de un evento activo). Documentar la fecha/hora de invalidación por tenant.

---

## 7. Archivos (FILES)

Copiar desde el storage origen (`storage/.../tenant<id>/`) al destino (`MEDIA_ROOT/<schema>/...`):

| Origen | Destino | Privado |
|---|---|---|
| `app/public/ine/*` | `media/<schema>/citas/ine/` o `proveedores/ine/` | **sí** |
| `app/public/photos/*` | `media/<schema>/empleados/fotos/` | controlado |
| gafetes PNG | no se copian (se reemiten, §6) | — |
| REPSE/SUA (proveedor) | `media/<schema>/proveedores/{repse,sua}/` | **sí** |
| docs de empleado | `media/<schema>/empleados/documentos/` | **sí** |
| protocolos PDF | `media/<schema>/protocolos/` | controlado |

Actualizar las rutas en los modelos cargados para que apunten al nuevo storage. Validar que cada
`FileField` referenciado existe físicamente; registrar faltantes.

---

## 8. Validación (VALIDATE) — criterio de aceptación del ETL

Por tenant, antes de dar el tenant por migrado:

1. **Conteos**: filas por tabla origen == filas destino (descontando lo intencionalmente no migrado,
   §10 del modelo). Reporte de diferencias justificadas.
2. **Integridad referencial**: cero FKs huérfanas; toda `GenericForeignKey` de `AsistenteCita`
   resuelve a un objeto existente; `parent_id` reconstruidos válidos o null.
3. **Muestras dirigidas**: N registros por entidad crítica (evento con proveedores y empleados, cita
   directa con asistentes e INE, registro de acceso con su contexto) revisados campo a campo.
4. **PII cifrada**: muestreo de `curp`/`ine_data`/`identification_number` en BD = ciphertext.
5. **Aislamiento**: dentro del `tenant_context` del tenant migrado no se ven datos de `public` ni de
   otros tenants (corre la suite de aislamiento del proyecto contra el schema recién cargado).
6. **Reglas de negocio**: `checkdocs` recomputado coincide con `statusdocs` migrado en una muestra;
   estados de evento/cita coherentes.

Solo con los 6 en verde el tenant pasa a producción.

---

## 9. Cutover y rollback

**Cutover por tenant** (no big-bang):
1. Migrar piloto (tenant de menor volumen) en entorno destino; validar (§8); operar en paralelo unos días.
2. Migrar el resto en orden de menor a mayor volumen.
3. **Congelar escrituras** en el tenant origen durante la ventana de corte (modo solo-lectura o
   mantenimiento), correr el ETL final delta, validar, apuntar el subdominio al destino, reemitir QR (§6).
4. Apagar el verificador/edge viejos del tenant (invalida QR viejos) y aprovisionar dispositivos con
   token nuevo.

**Rollback**: el pipeline es idempotente. Ante fallo de validación, `DROP SCHEMA <tenant> CASCADE`,
corregir el transform y reintentar. El origen permanece intacto (lectura) hasta el cutover final;
mientras no se apunte el subdominio, el sistema viejo sigue siendo la fuente de verdad.

---

## 10. Riesgos específicos del ETL

| Riesgo | Mitigación |
|---|---|
| `zones`/`accesses` con `name` unique global colisionan al pasar a unique por recinto | Detectar y deduplicar/renombrar en transform; reporte por tenant |
| `person_id` polimórfico apunta a id inexistente | Validar contra Contacto/Empleado; huérfano → registrar y dejar `persona` null |
| `verified` con valores fuera de {0,1,2} (drift boolean/int) | Auditar valores distintos antes de migrar; mapa explícito |
| `events.date` ≠ `vigencia_inicio` en algún tenant | Comparar y decidir caso por caso antes de descartar `date` |
| Gafetes vigentes durante el corte | Ventana fuera de evento activo + reemisión inmediata |
| Passwords no migrables (hash MySQL) | Flujo de reset obligatorio al primer login (usuarios y proveedores) |
| Volumen de archivos INE/fotos | Copia por streaming + verificación de existencia; reintentos |

---

## 11. Entregable de código (F8)

- Management command `migrar_tenant_sar <subdominio> [--dry-run] [--solo=tabla,...]`.
- Módulo `etl/` con: lectores MySQL por tabla, transformadores (mapas de enum, FK, polimorfismo,
  cifrado), cargadores ORM en `tenant_context`, copiador de archivos, reemisor de QR, validadores (§8).
- Reporte por tenant (conteos, diferencias, huérfanos, colisiones resueltas, PII verificada).
- Tests del ETL con un dataset sintético pequeño (sin PII real) que ejercite cada transformación.

---

*Fin del plan de migración de datos. Con este documento + `MODELO_DATOS_SAR.md` +
`REMEDIACION_SEGURIDAD_SAR.md`, la fase F8 del playbook tiene todo lo necesario para el traslado.*
