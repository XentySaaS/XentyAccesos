# MODELO_DATOS_SAR — Esquema destino limpio (Xenty Acceso)

> Esquema de datos destino para la reconstrucción del SAR sobre PostgreSQL/Django.
> Consolida el esquema **real** del sistema origen (migraciones `create` + todos los `alter`
> dispersos) y lo redefine **limpio**: typos corregidos, FKs faltantes añadidas, índices nuevos,
> tipos y enums normalizados, PII cifrada.
>
> Documento de referencia técnica de `PLAYBOOK_SAR_XENTY.md`. Cada modelo indica la fase (F0–F8)
> en que se implementa y la tabla MySQL de origen. Las migraciones de datos viven en
> `MIGRACION_DATOS_SAR.md`; los fixes de seguridad, en `REMEDIACION_SEGURIDAD_SAR.md`.

---

## 1. Principios del rediseño (aplican a todo el esquema)

1. **Nombres limpios en español, sin typos.** El nombre interno (modelo/tabla Postgres) se corrige;
   el mapeo a la tabla MySQL origen queda documentado para el ETL. Ver §3.
2. **Toda FK es real.** Las auto-referencias `parent_id` y los `*_id` "sueltos" del origen se
   convierten en `ForeignKey`/`GenericForeignKey` explícitas con `on_delete` definido.
3. **Índices donde el origen no los tenía** (reportes y filtros calientes): `RegistroAcceso` por
   tiempo, `DestinatarioMensaje.status`, `HistorialCambio.usuario`, etc. (§8).
4. **Enums → `TextChoices`/`IntegerChoices`.** Sin enums crudos; valores estables, etiqueta para UI.
5. **PII cifrada en reposo** (Fernet): `ine_data`, `identification_number`, `curp`, `nss`, imágenes
   de identificación. Storage privado por schema; nunca disco público.
6. **Sin borrado físico de personas.** `Empleado`/`Usuario` usan baja lógica (`activo=False` +
   `fecha_baja`), nunca `DELETE`. (Alinea con la regla de la suite: una baja congela, no elimina.)
7. **Fechas en UTC; `USE_TZ=True`.** `DateTimeField` para instantes; `DateField`/`TimeField` para
   vigencias y horarios. Se separa la duplicidad `start_time/end_time (date)` vs `hora_inicio/hora_fin`.
8. **Multitenancy**: modelos de `apps.tenants` y edge en schema `public`; el resto, por tenant (§5–6).

---

## 2. Equivalencia de tipos (Laravel/MySQL → Django/Postgres)

| Laravel | Django | Nota |
|---|---|---|
| `id()` | `BigAutoField` (implícito) | PK |
| `text()` corto (name, email, phone) | `CharField(max_length=…)` | el origen abusa de `text`; acotar |
| `text()` real (descripciones largas) | `TextField` | |
| `string()` | `CharField` | |
| `enum([...])` | `TextChoices` | etiqueta + valor estable |
| `tinyInteger` semáforo (0/1/2…) | `IntegerChoices` | nombrar los estados |
| `json()` | `JSONField` | |
| `boolean()` | `BooleanField` | |
| `date()` | `DateField` | |
| `time()` | `TimeField` | |
| `dateTime()` / `timestamp()` | `DateTimeField` | UTC |
| `foreignId()->constrained()` | `ForeignKey(..., on_delete=…)` | explicitar `on_delete` |
| `uuid()` | `UUIDField` | |
| PII (`curp`,`nss`,`ine_data`,…) | `EncryptedField` (Fernet) | §1.5 |

---

## 3. Tabla maestra de renombrados (origen → destino)

| Tabla MySQL origen | Modelo / tabla destino | Motivo |
|---|---|---|
| `assistent_appointments` | `AsistenteCita` / `asistentes_cita` | typo "assistent" |
| `result__lista69bs` | `ResultadoLista69b` / `resultados_lista69b` | doble `_` |
| `authorized_areas_event_supppliers` | `AreaAutorizadaEventoProveedor` / `areas_autorizadas_evento_proveedor` | "supppliers" (3 p) |
| `Change_history` (modelo) | `HistorialCambio` / `historial_cambios` | naming inconsistente |
| `lista_69bs` | `ConsultaLista69b` / `consultas_lista69b` | claridad |
| `devices_tenants` | `DispositivoEdge` / `dispositivos_edge` | claridad |
| `edge_commands` | `ComandoEdge` / `comandos_edge` | español |
| `options` | `Opcion` / `opciones` | clave-valor de config |
| `users` (tenant) | `Usuario` / `accounts_usuario` | contexto operación |
| `providers` | `CuentaProveedor` / `cuentas_proveedor` | distinguir de `Proveedor`(Supplier) |
| `suppliers` | `Proveedor` / `proveedores` | empresa externa |

> El resto conserva nombre traducido directo (events→eventos, employees→empleados, etc.).

---

## 4. Apps y fase de implementación

| App Django | Modelos | Fase | Schema |
|---|---|---|---|
| `apps.tenants` | Tenant, Domain, Plan, Suscripcion, SaldoCreditos, MovimientoCredito, IntentoPago, Factura, SuperAdmin, Version, VentanaMantenimiento, ConfiguracionMesa, **DispositivoEdge, ComandoEdge** | F0 | public |
| `apps.accounts` | Usuario | F0 | tenant |
| `apps.proveedores` | Proveedor, CuentaProveedor | F1 | tenant |
| `apps.empleados` | Empleado | F1 | tenant |
| `apps.recintos` | Recinto, Zona, Acceso, Ubicacion, Entrada, AreaAutorizada, Protocolo, (pivots áreas) | F1/F3 | tenant |
| `apps.documentos` | GrupoDocumentos, TipoDocumento, DocumentoEmpleado, (pivots evento↔doc) | F2 | tenant |
| `apps.eventos` | Evento, EventoProveedor, CajonParking, (pivots empleado/verifier) | F3 | tenant |
| `apps.citas` | Cita, AsistenteCita, Contacto | F4 | tenant |
| `apps.ocr` | (servicio; escribe `AsistenteCita.ine_data`) | F4 | tenant |
| `apps.gafetes` | (servicio de emisión QR/credencial) | F5 | tenant |
| `apps.acceso` | RegistroAcceso, RegistroAccesoParking | F5 | tenant |
| `apps.sanciones` | Sancion | F5 | tenant |
| `apps.dispositivos` | (vistas HMAC/long-poll; modelos en public) | F6 | tenant/public |
| `apps.mensajeria` | Mensaje, DestinatarioMensaje | F7 | tenant |
| `apps.cumplimiento` | SatEfo, ConsultaLista69b, ResultadoLista69b | F7 | tenant |
| `apps.config` | Opcion, HistorialCambio | F0/F8 | tenant |

---

## 5. CONTROL PLANE (schema `public`) — modelos específicos del SAR

El control plane Xenty (Tenant/Plan/Suscripcion/billing/MFA) se hereda del Fiscal (ver
`ARQUITECTURA_Y_STACK_TECNOLOGICO.md` §8). Los campos del `tenants` origen del SAR (`company`,
`trial_ends_at`, `subscription_status`, `subscription_plan`, `subscription_id`, `data`) se
**absorben** en el modelo `Tenant` de Xenty (estado `trial/activo/suspendido/cancelado`). Lo
**específico del SAR** que se añade a `public`:

```python
# apps/tenants/models.py  (additions)

class DispositivoEdge(models.Model):
    """Raspberry Pi en torniquetes/plumas. Origen: devices_tenants (BD central)."""
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE,
                               related_name="dispositivos")
    mac_address = models.CharField(max_length=32, unique=True)
    nombre = models.CharField(max_length=120)
    # Secreto HMAC. Se almacena cifrado (Fernet) o como hash; NUNCA en claro. Ver REMEDIACION §7.
    token = models.CharField(max_length=255, unique=True)
    precinct_id = models.BigIntegerField(null=True, blank=True)       # ref lógica al tenant
    access_point_id = models.BigIntegerField(null=True, blank=True)   # ref lógica al tenant
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

class ComandoEdge(models.Model):
    """Cola de comandos para dispositivos. Origen: edge_commands (BD central)."""
    class Tipo(models.TextChoices):
        RELAY_OPEN = "relay.open", "Abrir relé"
        DISPLAY_TEXT = "display.text", "Mostrar texto"
    class Estado(models.TextChoices):
        PENDING = "pending", "Pendiente"
        SENT = "sent", "Enviado"
        ACK = "ack", "Confirmado"
    dispositivo = models.ForeignKey(DispositivoEdge, on_delete=models.SET_NULL,
                                    null=True, related_name="comandos")
    tipo = models.CharField(max_length=50, choices=Tipo.choices)
    port = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    texto = models.CharField(max_length=255, null=True, blank=True)
    timeout_sec = models.PositiveIntegerField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices,
                              default=Estado.PENDING, db_index=True)
    # Anti-replay del long-poll/HMAC (REMEDIACION §7.7): nonce consumido por dispositivo.
    nonce = models.CharField(max_length=64, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
```

> **Decisión abierta**: edge en `public` (centralizado, gestionado por super-admin) vs. por tenant.
> Aquí se modela en `public` reflejando el origen. La validación cruzada de tenant es obligatoria
> en cada operación edge (REMEDIACION §7.7, hallazgo C7). Confirmar antes de F6.

---

## 6. DATA PLANE (schema por tenant) — modelos por app

### 6.1 `apps.accounts` — Usuario (origen: `users` tenant) · F0

```python
class Usuario(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        EDITOR = "editor", "Editor"
        GUARDIA = "guardia", "Guardia"              # Security Guard
        GERENTE = "gerente", "Gerente"              # Manager
        RECEPCION = "recepcion", "Recepcionista"    # Receptionist
        USUARIO = "usuario", "Usuario"
        VERIFICADOR = "verificador", "Verificador"  # Verifier
    nombre = models.CharField(max_length=160)
    email = models.EmailField(unique=True)
    email_verificado = models.DateTimeField(null=True, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.EDITOR)
    recinto = models.ForeignKey("recintos.Recinto", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="usuarios")
    telefono = models.CharField(max_length=30, null=True, blank=True)
    activo = models.BooleanField(default=True)         # reemplaza status=inactive
    fecha_baja = models.DateTimeField(null=True, blank=True)  # reemplaza low_login/delete_at
    # password (Argon2id), last_login → AbstractBaseUser
```

> Cambios: `role` enum → `Rol`; baja lógica `activo`+`fecha_baja` reemplaza el `low_login/delete_at`
> ad-hoc; se elimina `company_id` (vestigial en usuarios del tenant). El login exige `activo=True`.

### 6.2 `apps.proveedores` — Proveedor (Supplier) + CuentaProveedor (Provider) · F1

```python
class Proveedor(models.Model):  # origen: suppliers
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADO = "confirmado", "Confirmado"
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
    nombre = models.CharField(max_length=200)
    razon_social = models.CharField(max_length=255, null=True, blank=True)
    rfc = models.CharField(max_length=13, null=True, blank=True, db_index=True)
    email = models.EmailField(null=True, blank=True)
    email_responsable = models.EmailField(null=True, blank=True)
    nombre_responsable = models.CharField(max_length=200, null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    file_repse = models.FileField(upload_to="proveedores/repse/", null=True, blank=True)
    file_sua = models.FileField(upload_to="proveedores/sua/", null=True, blank=True)
    responsable = models.ForeignKey("proveedores.CuentaProveedor", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="proveedor_responsable")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)

class CuentaProveedor(AbstractBaseUser, PermissionsMixin):  # origen: providers (guard provider)
    class Rol(models.TextChoices):
        ADMIN = "admin", "Admin"
        USUARIO = "usuario", "Usuario"
    nombre = models.CharField(max_length=160)
    apellidos = models.CharField(max_length=160, null=True, blank=True)
    email = models.EmailField(unique=True)
    email_verificado = models.DateTimeField(null=True, blank=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.USUARIO)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE,
                                  null=True, related_name="cuentas")  # era company_id
    puesto = models.CharField(max_length=120, null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    activo = models.BooleanField(default=True)
    # PII cifrada (Fernet):
    curp = EncryptedCharField(max_length=18, null=True, blank=True)
    nss = EncryptedCharField(max_length=11, null=True, blank=True)
    file_ine = models.FileField(upload_to="proveedores/ine/", null=True, blank=True)  # disco PRIVADO
    foto = models.ImageField(upload_to="proveedores/fotos/", null=True, blank=True)
```

> `company_id` (proveedor) → FK real `proveedor`. `curp/nss` se cifran. `file_ine` a disco privado.
> Token de invitación de onboarding: **firmado** (no el AES-ECB origen) — ver REMEDIACION §7.3.

### 6.3 `apps.empleados` — Empleado (origen: `employees`) · F1

```python
class Empleado(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        BAJA = "baja", "Baja"          # terminated
    proveedor = models.ForeignKey("proveedores.CuentaProveedor", on_delete=models.CASCADE,
                                  related_name="empleados")  # era provider_id
    nombre = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)   # unique REMOVIDO en origen → no unique
    telefono = models.CharField(max_length=30, null=True, blank=True)
    foto = models.ImageField(upload_to="empleados/fotos/", null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
```

> Confirmar: `employees.provider_id` apunta a `providers` (CuentaProveedor), no a `suppliers`.
> La baja (`estado=baja`) congela, no elimina.

### 6.4 `apps.recintos` — topología física · F1 (áreas/protocolos F3)

```python
class Recinto(models.Model):                 # precincts
    nombre = models.CharField(max_length=200, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    codigo = models.CharField(max_length=60, unique=True, null=True, blank=True)

class Zona(models.Model):                    # zones
    recinto = models.ForeignKey(Recinto, on_delete=models.CASCADE, related_name="zonas")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    class Meta:
        unique_together = [("recinto", "nombre")]   # FIX: era unique global

class Acceso(models.Model):                  # accesses
    recinto = models.ForeignKey(Recinto, on_delete=models.CASCADE, related_name="accesos")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    class Meta:
        unique_together = [("recinto", "nombre")]   # FIX

class Ubicacion(models.Model):               # locations
    zona = models.ForeignKey(Zona, on_delete=models.CASCADE, related_name="ubicaciones")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    padre = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="hijas")   # FIX: parent_id ahora FK real

class Entrada(models.Model):                 # entries
    acceso = models.ForeignKey(Acceso, on_delete=models.CASCADE, related_name="entradas")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    padre = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="hijas")   # FIX: parent_id ahora FK real

class AreaAutorizada(models.Model):          # authorized_areas
    recinto = models.ForeignKey(Recinto, on_delete=models.CASCADE, related_name="areas")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    class Meta:
        unique_together = [("recinto", "nombre")]

class Protocolo(models.Model):               # protocols
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    archivo = models.FileField(upload_to="protocolos/", null=True, blank=True)  # PDF ≤10MB
    activo = models.BooleanField(default=True)
```

Pivots de áreas autorizadas (M2M con `through` si llevan metadatos, o `ManyToManyField`):
`AreaAutorizada ↔ Evento` (authorized_areas_events), `↔ Cita` (authorized_areas_appointments),
`↔ EventoProveedor` (`AreaAutorizadaEventoProveedor`, corrige typo "supppliers").

### 6.5 `apps.documentos` · F2

```python
class GrupoDocumentos(models.Model):         # group_documents
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)

class TipoDocumento(models.Model):           # list_documents
    grupo = models.ForeignKey(GrupoDocumentos, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="tipos")  # era group_documents_id
    nombre = models.CharField(max_length=160)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)

class DocumentoEmpleado(models.Model):       # employee_documents
    class Estado(models.IntegerChoices):
        PENDIENTE = 0, "Pendiente"
        VERIFICADO = 1, "Verificado"
        RECHAZADO = 2, "Rechazado"
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE,
                                 related_name="documentos")
    tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT)
    archivo = models.FileField(upload_to="empleados/documentos/")   # disco PRIVADO
    tipo_archivo = models.CharField(max_length=60)
    estado = models.IntegerField(choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
```

> **Drift resuelto**: el origen declaró `employee_documents.verified` como `boolean` en migración,
> pero el negocio usa 0/1/2 (`checkdocs`). Destino: `IntegerChoices` PENDIENTE/VERIFICADO/RECHAZADO.

Pivots evento↔documento: `event_group_documents` → `EventoGrupoDocumentos`
(`evento`, `grupo`, `type_validation`: 0=al menos uno, 1=todos) y `event_list_document` →
`EventoTipoDocumento` (`evento`, `tipo_documento`).

### 6.6 `apps.eventos` · F3

```python
class Evento(models.Model):                  # events
    class Estado(models.TextChoices):
        PROGRAMADO = "programado", "Programado"     # scheduled
        EN_CURSO = "en_curso", "En curso"           # ongoing
        COMPLETADO = "completado", "Completado"     # completed
        CANCELADO = "cancelado", "Cancelado"        # cancelled
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey("accounts.Usuario", on_delete=models.PROTECT,
                                   related_name="eventos")   # user_id
    recinto = models.ForeignKey("recintos.Recinto", on_delete=models.PROTECT)
    protocolo = models.ForeignKey("recintos.Protocolo", on_delete=models.PROTECT)
    vigencia_inicio = models.DateField()    # era start_time (DATE)
    vigencia_fin = models.DateField()       # era end_time (DATE); valida fin >= inicio
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROGRAMADO)
    verificadores = models.ManyToManyField("accounts.Usuario", through="VerificadorEvento",
                                           related_name="eventos_a_verificar")
    # `date` del origen se descarta (redundante con vigencia_inicio). Confirmar en ETL.

class EventoProveedor(models.Model):         # event_suppliers
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="proveedores")
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.CASCADE)
    protocolo = models.ForeignKey("recintos.Protocolo", on_delete=models.SET_NULL, null=True, blank=True)
    zona = models.ForeignKey("recintos.Zona", on_delete=models.SET_NULL, null=True, blank=True)       # alter
    acceso = models.ForeignKey("recintos.Acceso", on_delete=models.SET_NULL, null=True, blank=True)   # alter
    ubicacion = models.ForeignKey("recintos.Ubicacion", on_delete=models.SET_NULL, null=True,
                                  blank=True, related_name="es_ubicacion")          # location_id
    punto_acceso = models.ForeignKey("recintos.Ubicacion", on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="es_punto_acceso")    # access_point_id
    limite = models.IntegerField(default=0)         # limit de personas
    requiere_parking = models.BooleanField(default=False)   # req_parking 0/1
    cajones_parking = models.IntegerField(default=0)        # parking_slots
    notas = models.TextField(null=True, blank=True)
    empleados = models.ManyToManyField("empleados.Empleado", through="EmpleadoEventoProveedor")

class EmpleadoEventoProveedor(models.Model): # employee_event_supplier (pivot con statusdocs)
    class StatusDocs(models.IntegerChoices):
        PENDIENTES = 0, "Docs pendientes"
        CUMPLE = 1, "Cumple"
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE)
    evento_proveedor = models.ForeignKey(EventoProveedor, on_delete=models.CASCADE)
    statusdocs = models.IntegerField(choices=StatusDocs.choices, default=StatusDocs.PENDIENTES)

class VerificadorEvento(models.Model):       # verifiers_events
    usuario = models.ForeignKey("accounts.Usuario", on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)

class CajonParking(models.Model):            # parking_event_suppliers
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)  # va en el QR
    evento_proveedor = models.ForeignKey(EventoProveedor, on_delete=models.CASCADE,
                                         related_name="cajones")
```

### 6.7 `apps.citas` · F4

```python
class Contacto(models.Model):                # contacts
    nombre = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)

class Cita(models.Model):                    # appointments
    class Tipo(models.IntegerChoices):
        PROVEEDOR = 0, "Proveedor"
        DIRECTA = 1, "Directa"
    class TipoCita(models.TextChoices):
        PROGRAMADA = "programada", "Programada"     # scheduled
        WALK_IN = "walk_in", "Walk-in"
        EMERGENCIA = "emergencia", "Emergencia"
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        CANCELADA = "cancelada", "Cancelada"
    creado_por_usuario = models.ForeignKey("accounts.Usuario", on_delete=models.PROTECT,
                                           related_name="citas_creadas")  # user_id / created_by
    asignado_a = models.ForeignKey("accounts.Usuario", on_delete=models.SET_NULL, null=True,
                                   blank=True, related_name="citas_asignadas")  # assigned_to (FIX: era sin FK)
    nombre = models.CharField(max_length=200, null=True, blank=True)
    detalles = models.TextField(null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)   # time_start
    hora_fin = models.TimeField(null=True, blank=True)      # time_end
    limite = models.IntegerField(null=True, blank=True)
    tipo = models.IntegerField(choices=Tipo.choices, default=Tipo.PROVEEDOR)
    tipo_cita = models.CharField(max_length=12, choices=TipoCita.choices, default=TipoCita.PROGRAMADA)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    protocolo = models.ForeignKey("recintos.Protocolo", on_delete=models.PROTECT)
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.SET_NULL, null=True, blank=True)
    recinto = models.ForeignKey("recintos.Recinto", on_delete=models.PROTECT)
    ubicacion = models.ForeignKey("recintos.Ubicacion", on_delete=models.SET_NULL, null=True,
                                  blank=True, related_name="citas_ubicacion")
    punto_acceso = models.ForeignKey("recintos.Ubicacion", on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="citas_punto_acceso")
    acceso = models.ForeignKey("recintos.Acceso", on_delete=models.SET_NULL, null=True, blank=True)  # alter
    empleados = models.ManyToManyField("empleados.Empleado", through="EmpleadoCita")

class AsistenteCita(models.Model):           # assistent_appointments  → asistentes_cita
    class Tipo(models.IntegerChoices):
        CONTACTO = 0, "Contacto"
        EMPLEADO = 1, "Empleado"
    class Estado(models.IntegerChoices):
        PENDIENTE = 0, "Pendiente"
        CONFIRMADO = 1, "Confirmado"
        CANCELADO = 2, "Cancelado"
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name="asistentes")
    nombre = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)   # unique REMOVIDO en origen
    telefono = models.CharField(max_length=30, null=True, blank=True)
    estado = models.IntegerField(choices=Estado.choices, default=Estado.PENDIENTE)
    # person_id polimórfico (contacts|employees según type) → GenericForeignKey explícita (FIX)
    tipo = models.IntegerField(choices=Tipo.choices, default=Tipo.CONTACTO)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    persona = GenericForeignKey("content_type", "object_id")
    # INE / identificación — PII cifrada:
    requiere_ine = models.BooleanField(default=True)     # requires_ine
    ine_capturado = models.BooleanField(default=False)   # ine_filled
    ine_data = EncryptedJSONField(null=True, blank=True) # campos OCR (Fernet)
    path_ine = models.FileField(upload_to="citas/ine/", null=True, blank=True)  # disco PRIVADO
    tipo_identificacion = models.PositiveSmallIntegerField(null=True, blank=True)  # identification_type
    numero_identificacion = EncryptedCharField(max_length=64, null=True, blank=True)  # identification_number
    estado_adicional = models.PositiveSmallIntegerField(default=0)  # status_aditional

class EmpleadoCita(models.Model):            # employee_appointment
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE)
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE)
```

> **Polimorfismo resuelto**: `assistent_appointments.person_id` apuntaba a `contacts` o `employees`
> según `type`, sin FK. Destino: `GenericForeignKey`. El ETL llena `content_type`/`object_id`.

### 6.8 `apps.acceso` · F5

```python
class RegistroAcceso(models.Model):          # access_logs
    class TipoAcceso(models.TextChoices):
        ENTRADA = "entrada", "Entrada"       # entry
        DENEGADO = "denegado", "Denegado"    # denied
    class Metodo(models.TextChoices):
        QR = "qr", "QR"
        PLACA = "placa", "Placa"
        MANUAL = "manual", "Manual"
        TARJETA = "tarjeta", "Tarjeta"
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.SET_NULL, null=True, blank=True)
    asistente = models.ForeignKey("citas.AsistenteCita", on_delete=models.SET_NULL, null=True, blank=True)
    evento = models.ForeignKey("eventos.Evento", on_delete=models.SET_NULL, null=True, blank=True)
    cita = models.ForeignKey("citas.Cita", on_delete=models.SET_NULL, null=True, blank=True)
    cajon = models.ForeignKey("eventos.CajonParking", on_delete=models.SET_NULL, null=True, blank=True)  # parking_id
    tipo_acceso = models.CharField(max_length=10, choices=TipoAcceso.choices, default=TipoAcceso.ENTRADA)
    metodo = models.CharField(max_length=10, choices=Metodo.choices, default=Metodo.QR)
    placa_vehiculo = models.CharField(max_length=20, null=True, blank=True)
    hora_entrada = models.DateTimeField(db_index=True)             # FIX índice
    hora_salida = models.DateTimeField(null=True, blank=True, db_index=True)  # FIX índice
    observaciones = models.TextField(null=True, blank=True)

class RegistroAccesoParking(models.Model):   # access_log_parkings
    class TipoAcceso(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        DENEGADO = "denegado", "Denegado"
    cajon = models.ForeignKey("eventos.CajonParking", on_delete=models.CASCADE,
                              related_name="registros")   # parking_event_suppliers_id
    tipo_acceso = models.CharField(max_length=10, choices=TipoAcceso.choices, default=TipoAcceso.ENTRADA)
    hora_entrada = models.DateTimeField(db_index=True)
    hora_salida = models.DateTimeField(null=True, blank=True)
    personas = models.IntegerField(default=1)
    placa_vehiculo = models.CharField(max_length=20, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
```

### 6.9 `apps.sanciones` — Sancion (origen: `warnings`) · F5

```python
class Sancion(models.Model):
    class Severidad(models.TextChoices):
        BAJO = "bajo", "Bajo"; MEDIO = "medio", "Medio"; ALTO = "alto", "Alto"
    class Penalidad(models.TextChoices):
        ADVERTENCIA = "advertencia", "Advertencia"
        SUSPENSION = "suspension", "Suspensión"
        BAJA = "baja", "Baja"
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE, related_name="sanciones")
    evento = models.ForeignKey("eventos.Evento", on_delete=models.SET_NULL, null=True, blank=True)
    cita = models.ForeignKey("citas.Cita", on_delete=models.SET_NULL, null=True, blank=True)
    severidad = models.CharField(max_length=8, choices=Severidad.choices, null=True, blank=True)
    penalidad = models.CharField(max_length=12, choices=Penalidad.choices, null=True, blank=True)
    motivo = models.TextField()
    fecha_inicio = models.DateField(null=True, blank=True)   # obligatoria si penalidad=Suspensión
    fecha_fin = models.DateField(null=True, blank=True)
```

### 6.10 `apps.mensajeria` · F7

```python
class Mensaje(models.Model):                 # messages
    class Segmento(models.TextChoices):
        RECINTO = "recinto", "Recinto"; ZONA = "zona", "Zona"; EVENTO = "evento", "Evento"
        TODOS_EVENTOS = "todos_eventos", "Todos los eventos"
        TODOS_RECINTOS = "todos_recintos", "Todos los recintos"
        RECINTOS_Y_ZONAS = "recintos_y_zonas", "Recintos y zonas"
    class Estado(models.IntegerChoices):
        PENDIENTE = 0, "Pendiente"; EN_PROGRESO = 1, "En progreso"
        CANCELADO = 2, "Cancelado"; COMPLETADO = 3, "Completado"
    cuerpo = models.TextField()
    archivo = models.FileField(upload_to="mensajes/", null=True, blank=True)
    segmento = models.CharField(max_length=20, choices=Segmento.choices, default=Segmento.RECINTO)
    segmento_id = models.BigIntegerField(null=True, blank=True)  # id de recinto/zona/evento
    estado = models.IntegerField(choices=Estado.choices, default=Estado.PENDIENTE)
    progreso = models.FloatField(default=0)
    creado_por = models.ForeignKey("accounts.Usuario", on_delete=models.SET_NULL, null=True)

class DestinatarioMensaje(models.Model):     # message_recipients
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"; ENVIADO = "enviado", "Enviado"; FALLIDO = "fallido", "Fallido"
    mensaje = models.ForeignKey(Mensaje, on_delete=models.CASCADE, related_name="destinatarios")
    empleado = models.ForeignKey("empleados.Empleado", on_delete=models.CASCADE)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)  # FIX índice
    external_id = models.CharField(max_length=64, null=True, blank=True)   # id UltraMsg
```

### 6.11 `apps.cumplimiento` — SAT 69-B · F7

```python
class SatEfo(models.Model):                  # sat_efos (espejo CSV SAT)
    rfc = models.CharField(max_length=13, unique=True, db_index=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    situacion = models.CharField(max_length=40)  # Presunto|Definitivo|Desvirtuado|Sentencia Favorable
    meta = models.JSONField(null=True, blank=True)

class ConsultaLista69b(models.Model):        # lista_69bs
    tipo = models.IntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)

class ResultadoLista69b(models.Model):       # result__lista69bs → resultados_lista69b
    class Estado(models.IntegerChoices):
        LIMPIO = 0, "Limpio"; ENCONTRADO = 1, "Encontrado"
    consulta = models.ForeignKey(ConsultaLista69b, on_delete=models.CASCADE, related_name="resultados")
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.CASCADE)
    rfc = models.CharField(max_length=13, null=True, blank=True)
    query_data = models.JSONField(null=True, blank=True)
    estado = models.IntegerField(choices=Estado.choices, default=Estado.LIMPIO)
```

### 6.12 `apps.config` — Opcion + HistorialCambio · F0/F8

```python
class Opcion(models.Model):                  # options (key-value, helper get_option)
    clave = models.CharField(max_length=120, unique=True, db_index=True)
    valor = models.TextField(null=True, blank=True)

class HistorialCambio(models.Model):         # change_histories (Change_history)
    class Accion(models.TextChoices):
        CREADO="creado","Creado"; ACTUALIZADO="actualizado","Actualizado"
        ELIMINADO="eliminado","Eliminado"; RESTAURADO="restaurado","Restaurado"
        ASIGNADO="asignado","Asignado"; DESASIGNADO="desasignado","Desasignado"
        VISTO="visto","Visto"; LISTADO="listado","Listado"
    descripcion = models.TextField()
    modelo = models.CharField(max_length=120, null=True, blank=True)
    modelo_id = models.BigIntegerField(null=True, blank=True)
    usuario = models.ForeignKey("accounts.Usuario", on_delete=models.SET_NULL, null=True,
                                blank=True, db_index=True)   # FIX índice
    accion = models.CharField(max_length=12, choices=Accion.choices, default=Accion.CREADO)
    # DECISIÓN ABIERTA: diff before/after. Campos listos si se decide guardarlo:
    antes = models.JSONField(null=True, blank=True)
    despues = models.JSONField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["modelo", "modelo_id"])]
```

> **Decisión abierta** (del playbook §): hoy el origen NO guarda diff de columnas. Aquí dejo
> `antes`/`despues` (JSON, nullable) listos pero vacíos: si decides registrar el diff, se llenan
> sin cambiar el esquema; si no, no cuestan nada. Append-only (sin update/delete).

---

## 7. Roles y permisos (Spatie → Django)

El origen usa spatie/laravel-permission con tablas `permissions` (con columnas extra `seccion`,
`title`), `roles`, `model_has_*`, `role_has_permissions`. Destino:

- **Rol primario** vía el campo `rol` de `Usuario`/`CuentaProveedor` (enum estable, §6.1/6.2),
  evaluado por `RequiereRol(*roles)`.
- **Matriz de permisos por sección** (si se conserva la UI del origen): modelo `Permiso`
  (`seccion`, `titulo`, `clave`, `guard`) + relación rol↔permiso, o `auth.Permission` de Django con
  un catálogo `seccion`. No hardcodear IDs de rol (el origen ataba 1..6 a IDs de Spatie).
- **Módulos del tenant**: `RequiereModulo` (HTTP 402) gobierna acceso por módulo comercial.

---

## 8. Índices nuevos (no existían en el origen)

| Tabla destino | Índice | Razón |
|---|---|---|
| `acceso_registroacceso` | `hora_entrada`, `hora_salida` | reportes de acceso a escala |
| `mensajeria_destinatariomensaje` | `estado` | progreso de campañas |
| `config_historialcambio` | `usuario`, (`modelo`,`modelo_id`) | auditoría consultable |
| `proveedores_proveedor` | `rfc` | validación 69-B y búsqueda |
| `eventos_cajonparking` | `uuid` | resolución de QR de parking |
| `cumplimiento_satefo` | `rfc` (unique) | ya existía; conservar |

---

## 9. Drift modelo↔esquema resuelto (consolidado)

| Caso | Origen | Destino |
|---|---|---|
| `employee_documents.verified` | migración `boolean`, negocio 0/1/2 | `IntegerChoices` PENDIENTE/VERIFICADO/RECHAZADO |
| `event_group_documents.type_validation` | añadido en alter, sin enum | `IntegerChoices` AL_MENOS_UNO/TODOS |
| `employee_event_supplier.statusdocs` | añadido en alter (2026-03) | `IntegerChoices` PENDIENTES/CUMPLE |
| `assistent_appointments.*` (type, person_id, ine_*, identification_*, status_aditional) | 4 alters dispersos | consolidado en `AsistenteCita` (§6.7) |
| `appointments.created_by/assigned_to` | `unsignedBigInteger` sin FK | FK reales a `Usuario` |
| `events.status` | añadido en alter | enum `Estado` desde el inicio |
| `users.role` | 4 alters de enum (Manager→Receptionist→User→Verifier) | enum `Rol` final completo |
| `event_suppliers.zone_id/access_id/req_parking` | 3 alters | columnas desde el inicio |
| `locations.parent_id`, `entries.parent_id` | sin FK | `ForeignKey('self')` |

---

## 10. Lo que NO se migra

- `personal_access_tokens` (Sanctum) — sin uso activo; el destino usa JWT.
- Tablas de infraestructura Laravel (`jobs`, `cache`, `sessions`, `failed_jobs`, `job_batches`,
  `imports`/`exports`/`failed_import_rows`) — el destino usa Celery/Redis + APIs de DRF.
- `events.date` — redundante con `vigencia_inicio` (confirmar en ETL antes de descartar).
- Carpeta `temporal/` y cualquier `.env` versionado — prohibido (REMEDIACION §7.1).

---

*Fin del modelo de datos. Siguiente recomendado: `MIGRACION_DATOS_SAR.md` (ETL MySQL→Postgres por
tenant) o `REMEDIACION_SEGURIDAD_SAR.md` (hallazgos → fix en el stack nuevo), según prioridad.*
