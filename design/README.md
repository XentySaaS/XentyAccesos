# Handoff: Xenty Acceso — Control de accesos a recintos

## Overview
Xenty Acceso es el puesto de control digital de un recinto (estadios, museos, plantas industriales): gestiona torniquetes, plumas vehiculares, gafetes, casetas y el instante en que una credencial **se acepta o se rechaza**. El producto se compone de **tres SPAs**:

- **`acceso`** — operación interna del recinto (administradores, gerentes, recepción, guardias, verificadores). Densidad alta, teclado, rapidez.
- **`proveedores`** — autoservicio de empresas externas, mobile-first, guiado paso a paso.
- **`admin`** — control plane de super-administración Xenty. Sobrio, data-rich.

Toda la UI está en **español de México**. El elemento de firma del producto es la **pantalla de resultado del escaneo** (el veredicto del guardia): debe entenderse en <1 segundo, a un metro de distancia.

## About the Design Files
Los archivos `.dc.html` de este bundle son **referencias de diseño creadas en HTML** — prototipos que muestran la apariencia e intención, **no código de producción para copiar directamente**. La tarea es **recrear estos diseños en el entorno del codebase objetivo** usando sus patrones y librerías establecidas.

El stack objetivo definido en el brief es: **React 18 + Vite + shadcn/ui + TailwindCSS + Recharts + qrcode.react + lucide-react**. Implementa los diseños con esos componentes (Button, Input, Select, Dialog, Sheet, Tabs, Card, Table/DataTable, Badge, Toast, Tooltip, Calendar, Avatar, Skeleton, Alert, Command, Form). No portees el HTML literal: traduce cada pantalla a componentes shadcn/ui con Tailwind.

> Los `.dc.html` usan un runtime propio (`support.js`, `deck-stage.js`) solo para previsualización en la herramienta de diseño. **Ignóralos** al implementar; son andamiaje de render, no parte del producto.

## Fidelity
**Alta fidelidad (hifi).** Colores, tipografía, espaciado e interacciones están definidos. Recrea la UI con fidelidad usando los tokens de abajo, mapeados a la escala de Tailwind/shadcn de tu proyecto.

---

## Design Tokens

### Color
Define estos como variables CSS / tema de Tailwind. Nombres tal como en el brief:

| Token | Hex | Uso |
|---|---|---|
| `--ink-900` | `#0F1B2D` | Fondo de sidebar, cabeceras, modo escáner |
| `--ink-700` | `#1F3147` | Superficies oscuras secundarias |
| `--slate-100` | `#F1F4F8` | Fondo de app (claro) |
| `--slate-300` | `#CBD5E1` | Bordes / divisores |
| `--signal-600` | `#2563EB` | Primario de marca: acción, foco, enlaces, selección |
| `--permitido` | `#16A34A` | Verde acceso concedido |
| `--denegado` | `#DC2626` | Rojo acceso negado |
| `--advertencia` | `#D97706` | Ámbar precaución / sanción |

Tonos de apoyo usados (derívalos de la escala Tailwind slate/blue/green/red/amber):
- Texto cuerpo `#475569` (slate-600), texto tenue `#64748B` (slate-500), placeholder `#94A3B8` (slate-400), borde claro `#E2E8F0` (slate-200).
- Fondos de badge: verde `#DCFCE7`, azul `#DBEAFE`/`#EFF6FF`, ámbar `#FEF3C7`/`#FFFBEB`/`#FEF3C7`, rojo `#FEE2E2`, verde acción `#F0FDF4`.
- Azules de gráfica (barras, claro→oscuro): `#DBEAFE` `#BFDBFE` `#93C5FD` `#60A5FA` `#2563EB` `#3B82F6`.

**Reglas de uso:**
- `--signal-600` con **restricción**: solo acción primaria, foco, selección, enlaces. No como color decorativo.
- El **trío de acceso** (permitido/denegado/advertencia) **solo en estados de acceso reales**: escáner, bitácora, badges de estado. Nunca como adorno.

### Tipografía
- **Display / UI**: `Hanken Grotesk` (grotesca geométrica). Pesos 400/500/600/700/800. Títulos, números grandes y el veredicto del escáner. *(Alternativa en evaluación: `Geist`; aún no decidida — confirmar con diseño antes de fijar.)*
- **Datos / tabular**: misma familia con `font-variant-numeric: tabular-nums` en TODA hora, fecha y conteo, para que las columnas alineen.
- **Mono**: `Geist Mono` para folios de gafete, UUID de cajón, RFC, MAC de dispositivo.

Escala tipográfica (px, jerarquía aplicada en los mocks):
| Rol | Tamaño | Peso | Notas |
|---|---|---|---|
| Veredicto escáner | 30–46 (móvil/full) | 800 | El tamaño más grande del producto |
| Título de pantalla (h1) | 22–34 | 800 | `letter-spacing:-.01em` |
| Sección (h2) | 15–22 | 700 | |
| Cuerpo | 13–15 | 400 | `line-height:1.5` |
| Etiqueta / overline | 11–12 | 600 | `text-transform:uppercase; letter-spacing:.04–.08em` |
| Mono / folios | 11–16 | 400–500 | `Geist Mono` |

### Layout
- Rejilla de 12 columnas. Contenido máx ~1280px en `acceso` / `admin`. `proveedores` más estrecho, mobile-first.
- Densidad: cómoda en proveedores; **compacta en operación** (filas de tabla 40–44px, acciones por fila).
- Objetivos táctiles **≥44px** en `proveedores` y en el escáner.

### Border radius
- Inputs / botones: 8–9px. Cards: 10–12px. Cards grandes / modales: 14–18px. Pill/badge: 999px. Marco de móvil: 30–34px (borde 8–9px `--ink-900`).

### Shadow
- Card sutil: `0 1px 3px rgba(15,27,45,.10)`.
- Card elevada / panel: `0 12px 40px rgba(15,27,45,.14)`.
- Veredicto / modal: `0 16px 48px rgba(<color>,.3)`.

### Iconografía
`lucide-react`, trazo 2px, esquinas redondeadas. **El estado nunca se comunica solo por icono ni solo por color** — siempre icono + texto (+ color).

---

## Screens / Views

### SPA `acceso` — Operación

#### 1. Layout base (shell)
- **Sidebar** fijo, ancho ~236px, fondo `--ink-900`, texto `#CBD5E1`. Logo Xenty (cuadro `--signal-600` con cruz `+`) + selector de recinto (card `--ink-700`). Navegación gated por rol: Inicio · Calendario · Eventos · Citas · Proveedores · Empleados · Verificación · Escáner · Bitácora · Sanciones · Mensajería · Lista 69-B · Usuarios · Configuración. Ítem activo: fondo `--signal-600`, texto blanco, peso 600. Badge de conteo (ej. Verificación = 12) en ámbar. Pie: avatar + nombre + rol.
- **Topbar** ~60px, fondo blanco, borde inferior `#E2E8F0`. Buscador global (paleta de comandos, atajo ⌘K) máx 420px. Fecha/hora con `tabular-nums`. Avatar.
- **Contenido**: fondo `--slate-100`, padding 24px.

#### 2. Inicio (dashboard)
- Saludo h1 + subtítulo (eventos en curso). Botón primario "Crear evento".
- **4 tarjetas KPI** (grid 4 col, gap 14px): Invitados hoy (1,840), Ingresados (1,247, verde), Eventos en curso (2), Accesos denegados (38, rojo). Número 30px/800 con `tabular-nums`.
- Grid 1.4fr / 1fr: **gráfica "Accesos por hora"** (Recharts BarChart, paleta azul claro→oscuro) + **lista "Eventos en curso"** (cards con badge "En curso" verde + métrica de ingresados) y **alerta** ámbar (documentos por vencer, dispositivo silencioso).

#### 3. Verificación de documentos (bandeja inbox)
- Header con icono, título, badge "12 pendientes" ámbar, identidad del verificador. Filtrada a los eventos del verificador.
- **Lista izquierda** ~380px: tabs Pendientes/Aprobados/Rechazados; ítems con nombre, hora (`tabular-nums` mono), proveedor + tipo de documento. Ítem activo: fondo `#EFF6FF`, borde izquierdo 3px `--signal-600`.
- **Panel derecho**: cabecera del documento (título + persona/empresa) + badge "Pendiente". **Previsualización** de PDF/imagen centrada (placeholder con líneas). Barra de acción inferior: metadatos del archivo (mono) + botón **Rechazar** (outline rojo, pide motivo) + **Aprobar documento** (verde).

#### 4. Escáner (elemento de firma) — modo guardia
Modo **oscuro a pantalla completa** (`--ink-900`). Funciona con cámara **y** lector HID externo (entrada por teclado). Feedback redundante: color + icono + texto + sonido/vibración corta. Respeta `prefers-reduced-motion`.

- **En espera**: header con recinto · acceso · torniquete + pill "En línea" (punto verde). Evento actual. Visor central con marco de esquinas azul (`#60A5FA`) y línea de barrido animada (deshabilitar con reduced-motion). Texto "Acerca el gafete al lector". Pie: contador de accesos del turno (`tabular-nums`, ej. 1,247) + guardia.
- **PERMITIDO**: fondo `--permitido` a pantalla completa, ✓ grande (lucide `check`), palabra **PERMITIDO** 800, **foto** circular grande de la persona, nombre 26px/800, panel translúcido con Proveedor / Evento / Vigencia (`tabular-nums`). Auto-regresa al visor en ~2.5s o al tocar.
- **DENEGADO**: fondo `--denegado`, ✗ grande (lucide `x`), **motivo en texto enorme** (Sin documentos / Fuera de vigencia / Sanción activa / Gafete inválido / No pertenece a este recinto), foto si existe, nombre. **Requiere toque** para continuar (botón blanco "Entendido · continuar") — que el guardia lo lea.
- **ADVERTENCIA**: fondo `--advertencia`, triángulo lucide, "ACCESO CON NOTA", foto, nombre, nota (ej. "INE por vencer · 3 días"), botón "Permitir el paso".
- **Tres tratamientos del veredicto a decidir con diseño**: A) pleno color, B) panel dividido (banda de color + bloque tinta con datos), C) foto a sangre con degradado. Elegir uno antes de implementar.

> Otras pantallas de `acceso` descritas en el brief pero no mockeadas aún: Calendario (mensual/semanal con bloques → Sheet de detalle), Eventos (DataTable + detalle con tabs), Bitácora de accesos (DataTable densa, `tabular-nums`, "Registrar salida", export Excel), Sanciones, Mensajería (campaña con barra de progreso por destinatario), Lista 69-B. Implementar siguiendo los mismos patrones.

### SPA `proveedores` — Autoservicio (mobile-first)
Encabezado simple con logo del recinto anfitrión + datos de la empresa. Tono cálido y guiado.

#### 5. Onboarding (wizard numerado, 4 pasos)
Marco móvil. Header `--ink-900` (recinto + "Registro de proveedor"). **Barra de progreso** de 4 segmentos (completado=verde, actual=azul, pendiente=`#E2E8F0`) + "Paso N de 4". Validación inline, guardado por paso. Entra por enlace de invitación con vigencia (si expiró: estado claro + cómo pedir uno nuevo).
- **Paso 1 — Datos de la empresa**: Razón social, RFC (campo mono, borde activo `--signal-600`), Régimen fiscal (Select). Botón "Continuar" full-width ≥44px.
- **Paso 2 — Documentos REPSE/SUA**: ítems de documento con estado (cargado=verde con ✓ y fondo `#F0FDF4`; zona de carga activa=dashed azul `#EFF6FF`, "tomar foto o elegir archivo"; pendiente=gris). Validación de tipo y tamaño (máx 10MB) con mensaje claro.
- **Paso 3 — Responsable.**
- **Paso 4 — Confirmación**: header verde con ✓ "Registro completo", resumen (empresa, documentos en revisión, responsable), nota azul "Te avisaremos por WhatsApp y correo", botones "Ir a mis empleados" / "Volver al inicio".

#### 6. Mi gafete / credencial
Card con header azul (recinto + pill "Proveedor"), foto, nombre, empresa, **QR** (`qrcode.react`), folio mono (`VR-8F3A-1190`), franja inferior verde de vigencia (`tabular-nums`). Nota: "Muestra este código en el acceso. También llegó a tu WhatsApp."

> Otras pantallas de `proveedores`: Mis empleados (lista + alta, **captura de foto con cámara** con guía de encuadre, import Excel, estado activo/baja), Mis eventos/citas (semáforo cumple/faltan documentos), Carga de documentos (drag/drop o cámara, estado pendiente/verificado/rechazado con motivo visible), Asignación masiva (bloquea empleados sin documentos verificados o que exceden límite, explica por qué; al confirmar avisa que emite gafetes por WhatsApp/email).

### SPA `admin` — Control plane (sobrio)
Navegación lateral clara, estética corporativa (sidebar **claro** `#F8FAFC`, no la "sala de control" oscura).

#### 7. Dispositivos edge — estado en vivo
- Header: título + subtítulo ("Raspberry Pi en torniquetes · estado vía long-poll") + botón "Dar de alta dispositivo". Resumen de conteos por estado (en línea / silenciosos / dados de baja).
- **DataTable**: columnas Dispositivo · MAC (mono) · Recinto/acceso · Tenant · Estado · Acción. Estado con punto de color + texto + antigüedad (`tabular-nums`): **En línea** verde, **Silencioso** ámbar (fila con fondo `#FFFBEB`, punto pulsante — deshabilitar pulso con reduced-motion), **Dado de baja** gris (acción "Probar" deshabilitada). Acción "Probar" = enviar comando (abrir relé / mostrar texto). Pie: total + "actualizado hace Ns".

> Otras pantallas de `admin`: Tenants (DataTable trial/activo/suspendido/cancelado + detalle plan/suscripción/módulos/consumo), Planes y suscripciones, Billing/Stripe (facturas, créditos, modo sandbox visible si no hay clave), Ventanas de mantenimiento, ConfiguracionMesa, Métricas globales (Recharts).

---

## Interactions & Behavior
- **Navegación**: sidebar gated por rol (guardia ve sobre todo Escáner + Bitácora; verificador ve Verificación + sus eventos).
- **Escáner**: lectura → veredicto. Permitido/Advertencia auto-regresan (~2.5s) o por toque; Denegado **exige toque** explícito. Soporta lector HID (eventos de teclado) además de cámara. Sonido/vibración opcionales.
- **Verificación**: Aprobar (toast de confirmación) / Rechazar (abre input de motivo obligatorio).
- **Eventos**: "Cancelar" pide confirmación y avisa que notifica por WhatsApp.
- **Wizard proveedores**: validación inline por campo, guardado por paso, no avanza si faltan requisitos.
- **Asignación masiva**: bloquea selección inválida con explicación.
- **Mensajería**: barra de progreso real de envío por destinatario.
- **Edge**: estado en vivo vía long-poll; refresco de antigüedad continuo.

## States (vacío / carga / error)
- **Vacío**: invita a la acción ("Aún no hay eventos. Crea el primero."), nunca "Sin datos".
- **Carga**: Skeletons por sección, nunca pantalla bloqueada. Progreso real en envíos masivos y OCR.
- **Error**: explica qué pasó y el siguiente paso, en la voz del producto; sin disculpas vagas.

## State Management
- Sesión: usuario, rol, recinto seleccionado (gating de navegación y datos).
- Escáner: estado de máquina `espera → leyendo → {permitido|denegado|advertencia} → espera`; timer de auto-retorno; cola de lecturas; modo entrada (cámara | HID).
- Verificación: documento seleccionado, filtro de tab, mutaciones aprobar/rechazar (+motivo).
- Wizard proveedores: paso actual, datos por paso, validación, persistencia parcial.
- Edge: polling de estados de dispositivo (long-poll), timestamps relativos.
- Listas/DataTables: orden, filtro, paginación **server-side**.

## Writing / Voz
- **Sentence case** en todo.
- El botón dice **qué hace** ("Registrar salida", no "Enviar") y conserva el nombre en el toast ("Salida registrada").
- Los errores explican qué pasó y cómo seguir.
- Cohesión de vocabulario: una acción conserva su nombre de principio a fin.

## Accesibilidad
- Contraste AA (especialmente el veredicto del escáner). Foco de teclado visible.
- Estado **nunca solo por color**: icono + texto. `prefers-reduced-motion` respetado (sin barrido ni pulso). Objetivos táctiles generosos en `proveedores` y escáner.
- `tabular-nums` en toda hora/fecha/conteo.

## Assets
- **Iconos**: `lucide-react` (no SVG a mano).
- **QR**: `qrcode.react`.
- **Fuentes**: Hanken Grotesk + Geist Mono (Google Fonts). Geist como alternativa display pendiente de decisión.
- **Fotos de personas**: en los mocks son placeholders rayados — sustituir por las fotos reales de la credencial. Son centrales en el impacto del escáner.
- **Logo Xenty**: en los mocks es un placeholder (cuadro `--signal-600` con cruz). Sustituir por el logo real de la suite cuando exista; reconciliar tokens con la marca Xenty Fiscal/Nómina si aplica.

## Out of scope (no implementar)
- Panel de cliente de Mesa de Ayuda dentro de estas SPAs (solo se consume su API).
- Agente de IA de dominio / chat.
- No reproducir la estética del sistema viejo (Filament).

## Files
Referencias de diseño en este bundle (HTML; abrir en navegador para inspeccionar):
- `Xenty Acceso.dc.html` — lienzo con las 5 pantallas prioritarias + sistema + los 3 tratamientos del veredicto (la referencia visual más completa de las apps).
- `Xenty Acceso - Manual de identidad.dc.html` — deck de 18 láminas: tokens, tipografía, componentes, escáner y resúmenes de cada SPA.
- `support.js`, `deck-stage.js` — runtime de previsualización **a ignorar** en la implementación.
