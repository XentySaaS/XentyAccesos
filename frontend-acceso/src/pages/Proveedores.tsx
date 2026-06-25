import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

interface Proveedor {
  id: number;
  nombre: string;
  rfc: string | null;
  estado: string;
}

interface Pagina {
  results?: Proveedor[];
}

export default function Proveedores() {
  const [items, setItems] = useState<Proveedor[]>([]);
  const [nombre, setNombre] = useState("");
  const [rfc, setRfc] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [invitacion, setInvitacion] = useState<string | null>(null);

  async function cargar() {
    const { data } = await api.get<Pagina | Proveedor[]>("/api/proveedores/");
    setItems(Array.isArray(data) ? data : data.results ?? []);
  }

  useEffect(() => {
    cargar().catch(() => setError("No se pudo cargar la lista."));
  }, []);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/proveedores/", { nombre, rfc: rfc || null });
      setNombre("");
      setRfc("");
      await cargar();
    } catch {
      setError("No se pudo crear (RFC inválido o falta rol administrador).");
    }
  }

  async function invitar(id: number) {
    setInvitacion(null);
    try {
      const { data } = await api.post(`/api/proveedores/${id}/invitar/`);
      setInvitacion(data.token);
    } catch {
      setError("No se pudo generar la invitación.");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">Proveedores</h1>

      <form onSubmit={crear} className="flex flex-wrap items-end gap-3 rounded-lg bg-white p-4 shadow">
        <label className="flex flex-col text-sm">
          Nombre
          <input className="rounded border px-3 py-2" value={nombre}
            onChange={(e) => setNombre(e.target.value)} required />
        </label>
        <label className="flex flex-col text-sm">
          RFC
          <input className="rounded border px-3 py-2" value={rfc}
            onChange={(e) => setRfc(e.target.value)} />
        </label>
        <button className="rounded bg-slate-900 px-4 py-2 text-white" type="submit">
          Crear
        </button>
        {error && <p className="w-full text-sm text-red-600">{error}</p>}
      </form>

      {invitacion && (
        <p className="break-all rounded bg-emerald-50 p-3 text-xs text-emerald-800">
          Token de invitación (72h): {invitacion}
        </p>
      )}

      <table className="w-full overflow-hidden rounded-lg bg-white shadow">
        <thead className="bg-slate-100 text-left text-sm">
          <tr>
            <th className="px-4 py-2">Nombre</th>
            <th className="px-4 py-2">RFC</th>
            <th className="px-4 py-2">Estado</th>
            <th className="px-4 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id} className="border-t text-sm">
              <td className="px-4 py-2">{p.nombre}</td>
              <td className="px-4 py-2">{p.rfc}</td>
              <td className="px-4 py-2">{p.estado}</td>
              <td className="px-4 py-2">
                <button className="rounded border px-2 py-1 text-xs" onClick={() => invitar(p.id)}>
                  Invitar
                </button>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td className="px-4 py-6 text-center text-slate-400" colSpan={4}>
                Sin proveedores todavía.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
