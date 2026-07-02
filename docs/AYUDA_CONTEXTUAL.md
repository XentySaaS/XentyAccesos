# Ayuda contextual en formularios — el ícono ⓘ (`Ayuda`)

> Convención de diseño (NO NEGOCIABLE) del frontend tenant y del super-admin panel:
> **todo campo de captura lleva un ícono de ayuda ⓘ junto a su etiqueta** que, al clic,
> explica *para qué sirve / qué es*. El sistema maneja datos fiscales, legales y de
> seguridad social — el usuario no debe adivinar qué significa cada campo.
>
> Esta convención también está enunciada en [CLAUDE.md](../CLAUDE.md) §7 y
> [FRONTEND.md](FRONTEND.md) (checklist de formularios). Este archivo es el detalle.

---

## 1. Componente

[`frontend/src/components/Ayuda.tsx`](../frontend/src/components/Ayuda.tsx) — ícono `Info`
(lucide) dentro de un `Popover` de Radix (accesible y táctil; sin dependencias nuevas).

```tsx
export function Ayuda({ children }: { children: ReactNode }) { … }
```

- **Props:** solo `children` = el texto/JSX explicativo.
- **Accesibilidad:** el trigger es un `<button type="button" aria-label="¿Qué es este campo?">`;
  abre con clic o toque (no depende de hover).
- **Estilo:** ícono `h-3.5 w-3.5` en `text-muted-foreground`; el popover es `w-64`, texto `text-xs`.
- `type="button"` evita que dispare el `submit` del formulario que lo contiene.

> El panel super-admin tiene su propio `Ayuda` equivalente (mismo patrón) si llega a
> requerirlo; hoy la mayoría de la ayuda contextual vive en el SPA del tenant.

## 2. Patrón de uso

Envuelve **etiqueta + ayuda** en un contenedor flex. La `<Ayuda>` va como **hermana** del
`Label`, **nunca dentro**, para no romper la asociación `Label htmlFor` ↔ input:

```tsx
<div className="space-y-1.5">
  <div className="flex items-center gap-1.5">
    <Label htmlFor="campo">Etiqueta</Label>
    <Ayuda>Qué es y para qué sirve este campo (con ejemplo si ayuda).</Ayuda>
  </div>
  <Input id="campo" value={…} onChange={…} />
</div>
```

### Checkboxes
Pon la `<Ayuda>` como **hermana del `<label>`**, no dentro — si va dentro, el clic en el
ícono alterna el check:

```tsx
<label className="flex items-center gap-2 text-sm">
  <Checkbox checked={…} onChange={…} /> Permite pago anual
</label>
<Ayuda>Si se activa, el plan ofrece contratación anual con descuento.</Ayuda>
```

### En tablas (encabezados o renglones de resultado)
El ⓘ puede ir junto al texto de un `TableHead`/`TableCell` dentro de un `inline-flex`
(p. ej. el simulador de nómina rotula "ISR método óptimo" / "Costo patronal" con su ⓘ):

```tsx
<TableCell>
  <span className="inline-flex items-center gap-1.5">
    Costo patronal
    <Ayuda>Sueldo + cuotas patronales (IMSS/RT/INFONAVIT) + ISN.</Ayuda>
  </span>
</TableCell>
```

## 3. Reglas del contenido

- **Correcto respecto a la mecánica real** (fiscal/legal/IMSS). Reúsa los conceptos del
  backend (no inventes definiciones). Si el campo alimenta un cálculo, di a qué afecta.
- **Conciso** (1–3 frases) y con **ejemplo** cuando ayude (p. ej. "c_RegimenFiscal, p. ej. 601").
- Para **claves de catálogo SAT**, recuerda que el campo además debe ser **seleccionable**
  (`CatalogoSatSelect`/`EntitySelect`), no texto libre — la ayuda explica *qué* es la clave.

## 4. Dónde aplica

Todo formulario de captura del tenant: Empleados, Empresas/CSD, Centros de trabajo, Conceptos,
Nómina (periodos/movimientos), Política, Obligaciones, Datos fiscales de la factura, Simulador,
Suscripción, etc. **Referencia de estilo:**
[ConceptosPage.tsx](../frontend/src/features/nomina/ConceptosPage.tsx) y
[EmpleadoFormDialog.tsx](../frontend/src/features/empleados/EmpleadoFormDialog.tsx).

## 5. Checklist al crear/editar un formulario

- [ ] Cada campo de captura tiene su `<Ayuda>` junto a la etiqueta.
- [ ] La `<Ayuda>` es hermana del `Label`/`<label>` (no rompe `htmlFor`; no alterna checkboxes).
- [ ] El texto es correcto fiscal/legalmente y trae ejemplo si aplica.
- [ ] Campos de clave de catálogo → combo seleccionable + ayuda que explica la clave.

---

*Componente: [frontend/src/components/Ayuda.tsx](../frontend/src/components/Ayuda.tsx).
Convención enunciada en [CLAUDE.md](../CLAUDE.md) §7 y [FRONTEND.md](FRONTEND.md).*
