import { useEffect, useState } from "react";
import api from "../api/client";

interface Sancion {
  id: number;
  empleado: number;
  evento: number | null;
  cita: number | null;
  severidad: string | null;
  penalidad: string | null;
  motivo: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  creado: string;
}

interface Empleado { id: number; nombre: string; }

const SEVERIDAD_COLOR: Record<string, string> = {
  bajo: "bg-blue-100 text-blue-800",
  medio: "bg-yellow-100 text-yellow-800",
  alto: "bg-red-100 text-red-800",
};

const PENALIDAD_COLOR: Record<string, string> = {
  advertencia: "bg-yellow-100 text-yellow-800",
  suspension: "bg-orange-100 text-orange-800",
  baja: "bg-red-100 text-red-800",
};

export default function Sanciones() {
  const [sanciones, setSanciones] = useState<Sancion[]>([]);
  const [empleados, setEmpleados] = useState<Empleado[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    empleado: "", severidad: "bajo", penalidad: "advertencia",
    motivo: "", fecha_inicio: "", fecha_fin: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const cargar = () =>
    Promise.all([
      api.get("/api/sanciones/sanciones/"),
      api.get("/api/empleados/empleados/"),
    ]).then(([s, e]) => {
      setSanciones(s.data.results ?? s.data);
      setEmpleados(e.data.results ?? e.data);
    }).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      await api.post("/api/sanciones/sanciones/", {
        empleado: Number(form.empleado),
        severidad: form.severidad,
        penalidad: form.penalidad,
        motivo: form.motivo,
        fecha_inicio: form.penalidad === "suspension" ? form.fecha_inicio : null,
        fecha_fin: form.penalidad === "suspension" ? form.fecha_fin : null,
      });
      setShowForm(false);
      setForm({ empleado: "", severidad: "bajo", penalidad: "advertencia", motivo: "", fecha_inicio: "", fecha_fin: "" });
      cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  const nombreEmpleado = (id: number) => empleados.find((e) => e.id === id)?.nombre ?? `#${id}`;

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Sanciones</h1>
        <button onClick={() => setShowForm(true)} className="ml-auto rounded bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700">
          + Nueva sanción
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <form onSubmit={crear} className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Nueva sanción</h2>
            {error && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Empleado</label>
                <select required value={form.empleado} onChange={(e) => setForm({ ...form, empleado: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm">
                  <option value="">Seleccionar…</option>
                  {empleados.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600">Severidad</label>
                  <select value={form.severidad} onChange={(e) => setForm({ ...form, severidad: e.target.value })}
                    className="w-full rounded border px-2 py-1 text-sm">
                    <option value="bajo">Bajo</option>
                    <option value="medio">Medio</option>
                    <option value="alto">Alto</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600">Penalidad</label>
                  <select value={form.penalidad} onChange={(e) => setForm({ ...form, penalidad: e.target.value })}
                    className="w-full rounded border px-2 py-1 text-sm">
                    <option value="advertencia">Advertencia</option>
                    <option value="suspension">Suspensión</option>
                    <option value="baja">Baja</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Motivo</label>
                <textarea required rows={3} value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" placeholder="Describe el motivo de la sanción…" />
              </div>
              {form.penalidad === "suspension" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">Fecha inicio</label>
                    <input required type="date" value={form.fecha_inicio} onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
                      className="w-full rounded border px-2 py-1 text-sm" />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">Fecha fin</label>
                    <input required type="date" value={form.fecha_fin} onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
                      className="w-full rounded border px-2 py-1 text-sm" />
                  </div>
                </div>
              )}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded border px-4 py-1 text-sm">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded bg-red-600 px-4 py-1 text-sm text-white disabled:opacity-50">
                {saving ? "Guardando…" : "Registrar sanción"}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-slate-500">Cargando…</p>
      ) : sanciones.length === 0 ? (
        <p className="text-slate-400">No hay sanciones registradas.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b bg-slate-50 text-xs text-slate-500">
              <tr>
                {["Empleado", "Motivo", "Severidad", "Penalidad", "Período de suspensión", "Fecha"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sanciones.map((s) => (
                <tr key={s.id} className="border-b hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{nombreEmpleado(s.empleado)}</td>
                  <td className="max-w-xs truncate px-4 py-2 text-slate-600">{s.motivo}</td>
                  <td className="px-4 py-2">
                    {s.severidad && (
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERIDAD_COLOR[s.severidad] ?? "bg-slate-100 text-slate-700"}`}>
                        {s.severidad}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {s.penalidad && (
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PENALIDAD_COLOR[s.penalidad] ?? "bg-slate-100 text-slate-700"}`}>
                        {s.penalidad}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {s.fecha_inicio && s.fecha_fin ? `${s.fecha_inicio} → ${s.fecha_fin}` : "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-500">{new Date(s.creado).toLocaleDateString("es-MX")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
