/**
 * Ayuda contextual — ícono ⓘ junto a la etiqueta de un campo (ver docs/AYUDA_CONTEXTUAL.md).
 * Popover de Radix: accesible, funciona con toque y no depende de hover.
 */
import { ReactNode } from "react";
import * as Popover from "@radix-ui/react-popover";
import { Info } from "lucide-react";

export function Ayuda({ children }: { children: ReactNode }) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label="¿Qué es este campo?"
          className="inline-flex text-slate-400 hover:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
          style={{ "--tw-ring-color": "#2563EB" } as any}
        >
          <Info className="h-3.5 w-3.5" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="top"
          align="start"
          sideOffset={6}
          className="z-[100] w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs leading-relaxed text-slate-600 shadow-lg"
        >
          {children}
          <Popover.Arrow className="fill-white" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
