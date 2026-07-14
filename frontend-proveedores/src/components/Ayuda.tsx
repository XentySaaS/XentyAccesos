/**
 * Ayuda contextual — ícono ⓘ junto a la etiqueta de un campo (ver docs/AYUDA_CONTEXTUAL.md).
 *
 * Equivalente al `Ayuda` del SPA de operación, pero SIN dependencia nueva: la SPA de
 * proveedores no trae `@radix-ui/react-popover`. El popover se posiciona con `position: fixed`
 * calculado desde el botón para no recortarse dentro de modales con overflow (hace de "portal").
 * Abre con clic/toque (no depende de hover), cierra con clic afuera, Escape o scroll.
 */
import { ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Info } from "lucide-react";

const ANCHO = 256; // w-64

export function Ayuda({ children }: { children: ReactNode }) {
  const [abierto, setAbierto] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number; arriba: boolean }>({
    top: 0,
    left: 0,
    arriba: false,
  });
  const btnRef = useRef<HTMLButtonElement>(null);
  const popRef = useRef<HTMLDivElement>(null);

  const recalcular = () => {
    const btn = btnRef.current;
    if (!btn) return;
    const r = btn.getBoundingClientRect();
    const margen = 8;
    const espacioAbajo = window.innerHeight - r.bottom;
    const arriba = espacioAbajo < 140; // si no cabe abajo, se muestra arriba
    // Alineado al inicio del ícono, pero sin salirse del viewport por la derecha.
    const left = Math.min(r.left, window.innerWidth - ANCHO - margen);
    const top = arriba ? r.top - margen : r.bottom + margen;
    setPos({ top, left: Math.max(margen, left), arriba });
  };

  useLayoutEffect(() => {
    if (abierto) recalcular();
  }, [abierto]);

  useEffect(() => {
    if (!abierto) return;
    const cerrar = () => setAbierto(false);
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!btnRef.current?.contains(t) && !popRef.current?.contains(t)) setAbierto(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAbierto(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", cerrar, true);
    window.addEventListener("resize", cerrar);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", cerrar, true);
      window.removeEventListener("resize", cerrar);
    };
  }, [abierto]);

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        aria-label="¿Qué es este campo?"
        aria-expanded={abierto}
        onClick={() => setAbierto((v) => !v)}
        className="inline-flex text-slate-400 transition hover:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      {abierto && (
        <div
          ref={popRef}
          role="tooltip"
          style={{
            position: "fixed",
            top: pos.top,
            left: pos.left,
            width: ANCHO,
            transform: pos.arriba ? "translateY(-100%)" : undefined,
          }}
          className="z-[100] rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-normal leading-relaxed text-slate-600 shadow-lg"
        >
          {children}
        </div>
      )}
    </>
  );
}
