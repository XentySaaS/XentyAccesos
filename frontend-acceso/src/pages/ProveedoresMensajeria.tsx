import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

interface Disponible { clave: string; etiqueta: string; }
interface Preferencia {
  proveedores_orden: string[];
  failover_habilitado: boolean;
  reintentos: number;
  timeout_ms: number;
  proveedores_disponibles: Disponible[];
  actualizado?: string;
}

const INK = "#0F1B2D";
const inputCls =
  "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

export default function ProveedoresMensajeria() {
  const [disponibles, setDisponibles] = useState<Disponible[]>([]);
  const [orden, setOrden] = useState<string[]>([]);
  const [failover, setFailover] = useState(true);
  const [reintentos, setReintentos] = useState(1);
  const [timeout, setTimeoutMs] = useState(15000);
  const [actualizado, setActualizado] = useState<string | undefined>();
  const [msg, setMsg] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [cargando, setCargando] = useState<string | null>("init");

  function aplicar(data: Preferencia) {
    setDisponibles(data.proveedores_disponibles ?? []);
    // Solo conserva claves aún disponibles (por si el master switch del Connector cambió).
    const validas = new Set((data.proveedores_disponibles ?? []).map((d) => d.clave));
    setOrden((data.proveedores_orden ?? []).filter((c) => validas.has(c)));
    setFailover(data.failover_habilitado);
    setReintentos(data.reintentos);
    setTimeoutMs(data.timeout_ms);
    setActualizado(data.actualizado);
  }

  async function cargar() {
    try {
      const { data } = await api.get<Preferencia>("/api/mensajeria/preferencia/");
      aplicar(data);
    } finally {
      setCargando(null);
    }
  }

  useEffect(() => { cargar(); }, []);

  const etiqueta = (clave: string) =>
    disponibles.find((d) => d.clave === clave)?.etiqueta ?? clave;
  const sinUsar = disponibles.filter((d) => !orden.includes(d.clave));

  function añadir(clave: string) { setOrden((o) => [...o, clave]); }
  function quitar(clave: string) { setOrden((o) => o.filter((c) => c !== clave)); }
  function mover(i: number, delta: number) {
    setOrden((o) => {
      const j = i + delta;
      if (j < 0 || j >= o.length) return o;
      const copia = [...o];
      [copia[i], copia[j]] = [copia[j], copia[i]];
      return copia;
    });
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setCargando("guardar");
    try {
      const { data } = await api.put<Preferencia>("/api/mensajeria/preferencia/", {
        proveedores_orden: orden,
        failover_habilitado: failover,
        reintentos,
        timeout_ms: timeout,
      });
      aplicar(data);
      setMsg({ tipo: "ok", texto: "Preferencia guardada." });
    } catch (err: any) {
      const detalle = err?.response?.data?.proveedores_orden?.[0];
      setMsg({ tipo: "error", texto: detalle || "No se pudo guardar la preferencia." });
    } finally {
      setCargando(null);
    }
  }

  if (cargando === "init") {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Mensajería · Proveedores</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Elige qué proveedores de WhatsApp usa tu organización y en qué orden. El primero es el
          principal; si falla, el sistema pasa al siguiente (failover).
        </p>
      </div>

      {msg && (
        <div className={`mb-4 rounded-lg px-4 py-2.5 text-sm ring-1 ${
          msg.tipo === "ok" ? "bg-green-50 text-green-700 ring-green-100" : "bg-red-50 text-red-700 ring-red-100"
        }`}>{msg.texto}</div>
      )}

      <form onSubmit={guardar} className="space-y-4">
        {/* Orden de proveedores */}
        <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
          <h2 className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            Orden de proveedores
            <Ayuda>
              Prioridad de arriba hacia abajo. El proveedor 1 recibe los envíos; si no está disponible
              y el failover está activo, se intenta el siguiente. Sin ninguno seleccionado, se usa el
              proveedor por defecto del sistema.
            </Ayuda>
          </h2>

          {orden.length === 0 ? (
            <p className="mt-2 rounded-lg bg-slate-50 px-3 py-4 text-center text-xs text-slate-400">
              Ningún proveedor seleccionado. Se usará el proveedor por defecto del sistema.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {orden.map((clave, i) => (
                <li key={clave} className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#2563EB] text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  <span className="flex-1 text-sm font-medium text-slate-700">{etiqueta(clave)}</span>
                  <div className="flex items-center gap-1">
                    <button type="button" onClick={() => mover(i, -1)} disabled={i === 0}
                      className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 disabled:opacity-30" title="Subir">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 15l-6-6-6 6"/></svg>
                    </button>
                    <button type="button" onClick={() => mover(i, 1)} disabled={i === orden.length - 1}
                      className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 disabled:opacity-30" title="Bajar">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>
                    </button>
                    <button type="button" onClick={() => quitar(clave)}
                      className="ml-1 rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Quitar">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {sinUsar.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
              <span className="text-xs text-slate-400">Añadir:</span>
              {sinUsar.map((d) => (
                <button key={d.clave} type="button" onClick={() => añadir(d.clave)}
                  className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
                  {d.etiqueta}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Failover y reintentos */}
        <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Failover y reintentos</h2>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={failover} onChange={(e) => setFailover(e.target.checked)} />
            <span className="flex items-center gap-1.5">
              Failover habilitado
              <Ayuda>
                Si el proveedor principal falla, intenta con el siguiente de la lista. Desactivado,
                solo se usa el proveedor principal (sin respaldo).
              </Ayuda>
            </span>
          </label>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 flex items-center gap-1.5 font-medium text-slate-700">
                Reintentos por proveedor
                <Ayuda>Cuántas veces se reintenta con un mismo proveedor antes de pasar al siguiente.</Ayuda>
              </span>
              <input type="number" min={0} max={10} value={reintentos}
                onChange={(e) => setReintentos(Number(e.target.value))} className={inputCls} />
            </label>
            <label className="block text-sm">
              <span className="mb-1 flex items-center gap-1.5 font-medium text-slate-700">
                Timeout por intento (ms)
                <Ayuda>Tiempo máximo de espera de un intento de envío antes de considerarlo fallido.</Ayuda>
              </span>
              <input type="number" min={500} value={timeout}
                onChange={(e) => setTimeoutMs(Number(e.target.value))} className={inputCls} />
            </label>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button type="submit" disabled={cargando !== null}
            className="rounded-lg bg-[#2563EB] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
            {cargando === "guardar" ? "Guardando…" : "Guardar preferencia"}
          </button>
          {actualizado && (
            <span className="text-xs text-slate-400">
              Actualizado: {new Date(actualizado).toLocaleString("es-MX")}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
