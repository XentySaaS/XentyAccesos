import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

interface Evento {
  id: number;
  nombre: string;
  estado: string;
  vigencia_inicio: string;
  vigencia_fin: string;
  recinto: number;
}
interface Recinto {
  id: number;
  nombre: string | null;
}
interface Pagina<T> {
  results?: T[];
}

const COLOR: Record<string, string> = {
  programado: "bg-blue-100 text-blue-700",
  en_curso: "bg-emerald-100 text-emerald-700",
  completado: "bg-slate-200 text-slate-700",
  cancelado: "bg-red-100 text-red-700",
};

function lista<T>(data: Pagina<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results ?? [];
}

export default function Eventos() {
  const [items, setItems] = useState<Evento[]>([]);
  const [recintos, setRecintos] = useState<Recinto[]>([]);
  const [f, setF] = useState({ nombre: "", recinto: "", vigencia_inicio: "", vigencia_fin: "" });
  const [error, setError] = useState<string | null>(null);

  async function cargar() {
    const [ev, rec] = await Promise.all([
      api.get<Pagina<Evento> | Evento[]>("/api/eventos/"),
      api.get<Pagina<Recinto> | Recinto[]>("/api/recintos/"),
    ]);
    setItems(lista(ev.data));
    setRecintos(lista(rec.data));
  }

  useEffect(() => {
    cargar().catch(() => setError("No se pudo cargar."));
  }, []);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/eventos/", { ...f, recinto: Number(f.recinto) });
      setF({ nombre: "", recinto: "", vigencia_inicio: "", vigencia_fin: "" });
      await cargar();
    } catch {
      setError("No se pudo crear (revisa vigencias y rol).");
    }
  }

  async function accion(ev: Evento, nombre: "iniciar" | "completar" | "cancelar") {
    try {
      await api.post(`/api/eventos/${ev.id}/${nombre}/`);
      await cargar();
    } catch {
      setError("Transición no permitida.");
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-semibold">Eventos</h1>

      <form onSubmit={crear} className="grid grid-cols-2 gap-3 rounded-lg bg-white p-4 shadow md:grid-cols-5">
        <input className="rounded border px-3 py-2" placeholder="Nombre" value={f.nombre}
          onChange={(e) => setF({ ...f, nombre: e.target.value })} required />
        <select className="rounded border px-3 py-2" value={f.recinto}
          onChange={(e) => setF({ ...f, recinto: e.target.value })} required>
          <option value="">Recinto…</option>
          {recintos.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
        </select>
        <input className="rounded border px-3 py-2" type="date" value={f.vigencia_inicio}
          onChange={(e) => setF({ ...f, vigencia_inicio: e.target.value })} required />
        <input className="rounded border px-3 py-2" type="date" value={f.vigencia_fin}
          onChange={(e) => setF({ ...f, vigencia_fin: e.target.value })} required />
        <button className="rounded bg-slate-900 px-4 py-2 text-white" type="submit">Crear</button>
        {error && <p className="col-span-full text-sm text-red-600">{error}</p>}
      </form>

      <table className="w-full overflow-hidden rounded-lg bg-white shadow">
        <thead className="bg-slate-100 text-left text-sm">
          <tr>
            <th className="px-4 py-2">Evento</th><th className="px-4 py-2">Vigencia</th>
            <th className="px-4 py-2">Estado</th><th className="px-4 py-2">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((ev) => (
            <tr key={ev.id} className="border-t text-sm">
              <td className="px-4 py-2">{ev.nombre}</td>
              <td className="px-4 py-2 text-slate-500">{ev.vigencia_inicio} → {ev.vigencia_fin}</td>
              <td className="px-4 py-2">
                <span className={`rounded px-2 py-0.5 text-xs ${COLOR[ev.estado] ?? ""}`}>{ev.estado}</span>
              </td>
              <td className="px-4 py-2 space-x-1">
                {ev.estado === "programado" && (
                  <button className="rounded border px-2 py-1 text-xs" onClick={() => accion(ev, "iniciar")}>Iniciar</button>
                )}
                {ev.estado === "en_curso" && (
                  <button className="rounded border px-2 py-1 text-xs" onClick={() => accion(ev, "completar")}>Completar</button>
                )}
                {(ev.estado === "programado" || ev.estado === "en_curso") && (
                  <button className="rounded border px-2 py-1 text-xs text-red-600" onClick={() => accion(ev, "cancelar")}>Cancelar</button>
                )}
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td className="px-4 py-6 text-center text-slate-400" colSpan={4}>Sin eventos.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
