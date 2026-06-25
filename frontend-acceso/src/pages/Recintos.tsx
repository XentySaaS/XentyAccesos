import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

interface Recinto {
  id: number;
  nombre: string | null;
  codigo: string | null;
  telefono: string | null;
}

interface Pagina {
  results?: Recinto[];
}

export default function Recintos() {
  const [items, setItems] = useState<Recinto[]>([]);
  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function cargar() {
    const { data } = await api.get<Pagina | Recinto[]>("/api/recintos/");
    setItems(Array.isArray(data) ? data : data.results ?? []);
  }

  useEffect(() => {
    cargar().catch(() => setError("No se pudo cargar la lista."));
  }, []);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/recintos/", { nombre, codigo: codigo || null });
      setNombre("");
      setCodigo("");
      await cargar();
    } catch {
      setError("No se pudo crear (¿tienes rol administrador?).");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">Recintos</h1>

      <form onSubmit={crear} className="flex flex-wrap items-end gap-3 rounded-lg bg-white p-4 shadow">
        <label className="flex flex-col text-sm">
          Nombre
          <input className="rounded border px-3 py-2" value={nombre}
            onChange={(e) => setNombre(e.target.value)} required />
        </label>
        <label className="flex flex-col text-sm">
          Código
          <input className="rounded border px-3 py-2" value={codigo}
            onChange={(e) => setCodigo(e.target.value)} />
        </label>
        <button className="rounded bg-slate-900 px-4 py-2 text-white" type="submit">
          Crear
        </button>
        {error && <p className="w-full text-sm text-red-600">{error}</p>}
      </form>

      <table className="w-full overflow-hidden rounded-lg bg-white shadow">
        <thead className="bg-slate-100 text-left text-sm">
          <tr>
            <th className="px-4 py-2">ID</th>
            <th className="px-4 py-2">Nombre</th>
            <th className="px-4 py-2">Código</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id} className="border-t text-sm">
              <td className="px-4 py-2">{r.id}</td>
              <td className="px-4 py-2">{r.nombre}</td>
              <td className="px-4 py-2">{r.codigo}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td className="px-4 py-6 text-center text-slate-400" colSpan={3}>
                Sin recintos todavía.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
