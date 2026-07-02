# Glosario — Xenty Acceso

| Término | Definición |
|---|---|
| **Acceso** | Punto de entrada físico a un recinto (modelo `recintos.Acceso`); también se refiere al registro de entrada/salida (`acceso.RegistroAcceso`) |
| **AreaAutorizada** | Zona permitida para un proveedor/evento/cita dentro del recinto |
| **AsistenteCita** | Persona invitada a una cita (puede ser Contacto o Empleado vía GenericFK) |
| **AuditViewSetMixin** | Mixin que registra automáticamente creaciones, ediciones y bajas en `HistorialCambio` |
| **Cita** | Reunión programada en un recinto (directa o de proveedor). Modelo en `apps/citas` |
| **Contacto** | Persona externa sin vínculo con proveedor (para citas directas) |
| **Control plane** | Plano de gestión: schema `public`, super-admin, billing, provisioning |
| **ctx** | Claim JWT que indica el contexto de autenticación: `"acceso"` o `"proveedores"` |
| **CuentaProveedor** | Cuenta de login de una empresa proveedora (contexto `proveedores`) |
| **Data plane** | Plano operativo: schema por tenant, operación del recinto |
| **EmpleadoCita** | Empleado de proveedor asignado a una cita |
| **Empleado** | Trabajador de la empresa proveedora, registrado por la `CuentaProveedor` |
| **Evento** | Actividad programada en un recinto con proveedores y empleados asignados |
| **EventoProveedor** | Relación N:M entre evento y proveedor (incluye parking, áreas, estatus) |
| **Fernet** | Esquema de cifrado autenticado (AES-128-CBC + HMAC-SHA256) usado para QR tokens |
| **Gafete** | Pase de acceso con código QR generado por `componer_gafete()` (diseño Premium Dark) |
| **Guardia** | Rol de usuario — acceso a scanner QR, sanciones, bitácora |
| **HistorialCambio** | Registro de auditoría (append-only) en `apps/config` |
| **INE** | Instituto Nacional Electoral — documento de identidad mexicano; datos cifrados con Fernet |
| **jti** | JWT ID / nonce único por token QR para prevenir replay attacks |
| **Middleware enforcement** | Stack de middlewares que bloquean acceso por estado del tenant (inactivo, trial expirado, solo-lectura, MFA incompleta) |
| **PermisoUsuario** | Permisos granulares para rol "usuario" — ver/crear/editar/eliminar por módulo |
| **Protocolo** | Reglas de acceso definidas para un recinto (documentos requeridos, horarios, etc.) |
| **Recinto** | Venue/instalación controlada (estadio, museo, planta). Modelo raíz de topología |
| **REPSE** | Registro de Prestadoras de Servicios Especializados — documento de cumplimiento laboral México |
| **RequiereModulo** | Permission class que verifica si el plan del tenant incluye el módulo solicitado (402 si no) |
| **RequierePermisoPersonalizado** | Permission class para permisos granulares del rol "usuario" |
| **RequiereRol** | Permission class que valida `user.rol` contra lista de roles permitidos |
| **SAR** | Sistema de Acceso a Recintos — nombre interno del proyecto |
| **SAT 69-B** | Artículo del Código Fiscal mexicano — lista de contribuyentes incumplidos |
| **Schema** | Schema PostgreSQL que aísla datos de un tenant (equivale a BD separada en el origen) |
| **Tenant** | Cliente/organización con schema PostgreSQL propio. Acceso vía subdominio |
| **Ubicación** | Lugar específico dentro de una zona (puede tener padre → jerarquía) |
| **UltraMsg** | Proveedor de API para envío de mensajes WhatsApp |
| **Usuario** | Staff del recinto en contexto `acceso` (roles: administrador, editor, guardia, verificador, recepcion, usuario) |
| **Verificador** | Rol de usuario — solo puede verificar documentos de empleados asignados a eventos |
| **Zona** | Subdivisión de un recinto (contiene ubicaciones) |
