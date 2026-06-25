import { useEffect, useState } from "react";
import api from "../api/client";

interface Cita {
  id: number;
  nombre: string;
  fecha: string;
  hora_inicio: string;
  hora_fin: string;
  tipo: number;
  tipo_cita: string;
  estado: string;
  proveedor: number | null;
  recinto: number;
}

interface Recinto { id: number; nombre: string; }
interface Proveedor { id: number; nombre: string; }

const TIPO_CITA_LABEL: Record<string, string> = {
  programada: "Programada", walk_in: "Walk-in", emergencia: "Emergencia",
};

const ESTADO_COLOR: Record<string, string> = {
  pendiente: "bg-yellow-100 text-yellow-800",
  confirmada: "bg-green-100 text-green-800",
  cancelada: "bg-red-100 text-red-800",
};

export default function Citas() {
  const [citas, setCitas] = useState<Cita[]>([]);
  const [recintos, setRecintos] = useState<Recinto[]>([]);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState("");
  const [form, setForm] = useState({
    nombre: "", fecha: "", hora_inicio: "", hora_fin: "",
    tipo: 0, tipo_cita: "programada", estado: "pendiente",
    recinto: "", proveedor: "", limite: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const cargar = () => {
    const params: Record<string, string> = {};
    if (filtroEstado) params.estado = filtroEstado;
    Promise.all([
      api.get("/api/citas/citas/", { params }),
      api.get("/api/recintos/recintos/"),
      api.get("/api/proveedores/proveedores/"),
    ]).then(([c, r, p]) => {
      setCitas(c.data.results ?? c.data);
      setRecintos(r.data.results ?? r.data);
      setProveedores(p.data.results ?? p.data);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [filtroEstado]);

  const cambiarEstado = (id: number, estado: string) =>
    api.patch(`/api/citas/citas/${id}/`, { estado }).then(cargar);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      await api.post("/api/citas/citas/", {
        nombre: form.nombre, fecha: form.fecha,
        hora_inicio: form.hora_inicio || null, hora_fin: form.hora_fin || null,
        tipo: Number(form.tipo), tipo_cita: form.tipo_cita, estado: "pendiente",
        recinto: Number(form.recinto),
        proveedor: form.proveedor ? Number(form.proveedor) : null,
        limite: form.limite ? Number(form.limite) : null,
      });
      setShowForm(false);
      setForm({ nombre: "", fecha: "", hora_inicio: "", hora_fin: "", tipo: 0, tipo_cita: "programada", estado: "pendiente", recinto: "", proveedor: "", limite: "" });
      cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Citas</h1>
        <div className="ml-auto flex gap-2">
          <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}
            className="rounded border px-2 py-1 text-sm">
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendiente</option>
            <option value="confirmada">Confirmada</option>
            <option value="cancelada">Cancelada</option>
          </select>
          <button onClick={() => setShowForm(true)}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">
            + Nueva cita
          </button>
        </div>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <form onSubmit={crear} className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Nueva cita</h2>
            {error && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="mb-1 block text-xs font-medium text-slate-600">Nombre / motivo</label>
                <input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" placeholder="Reunión de proveedores…" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Fecha</label>
                <input required type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Límite de asistentes</label>
                <input type="number" min="1" value={form.limite} onChange={(e) => setForm({ ...form, limite: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" placeholder="Sin límite" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Hora inicio</label>
                <input type="time" value={form.hora_inicio} onChange={(e) => setForm({ ...form, hora_inicio: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Hora fin</label>
                <input type="time" value={form.hora_fin} onChange={(e) => setForm({ ...form, hora_fin: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Tipo</label>
                <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: Number(e.target.value) })}
                  className="w-full rounded border px-2 py-1 text-sm">
                  <option value={0}>Proveedor</option>
                  <option value={1}>Directa</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Tipo de cita</label>
                <select value={form.tipo_cita} onChange={(e) => setForm({ ...form, tipo_cita: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm">
                  <option value="programada">Programada</option>
                  <option value="walk_in">Walk-in</option>
                  <option value="emergencia">Emergencia</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Recinto</label>
                <select required value={form.recinto} onChange={(e) => setForm({ ...form, recinto: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm">
                  <option value="">Seleccionar…</option>
                  {recintos.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Proveedor</label>
                <select value={form.proveedor} onChange={(e) => setForm({ ...form, proveedor: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm">
                  <option value="">Sin proveedor</option>
                  {proveedores.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded border px-4 py-1 text-sm">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded bg-blue-600 px-4 py-1 text-sm text-white disabled:opacity-50">
                {saving ? "Guardando…" : "Crear cita"}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-slate-500">Cargando…</p>
      ) : citas.length === 0 ? (
        <p className="text-slate-400">No hay citas registradas.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b bg-slate-50 text-xs text-slate-500">
              <tr>
                {["Nombre / motivo", "Fecha", "Horario", "Tipo", "Estado", "Acciones"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {citas.map((c) => (
                <tr key={c.id} className="border-b hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{c.nombre || `Cita #${c.id}`}</td>
                  <td className="px-4 py-2 text-slate-600">{c.fecha ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {c.hora_inicio && c.hora_fin ? `${c.hora_inicio.slice(0, 5)} – ${c.hora_fin.slice(0, 5)}` : "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-600">{TIPO_CITA_LABEL[c.tipo_cita] ?? c.tipo_cita}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_COLOR[c.estado] ?? "bg-slate-100 text-slate-700"}`}>
                      {c.estado}
                    </span>
                  </td>
                  <td className="flex gap-1 px-4 py-2">
                    {c.estado === "pendiente" && (
                      <button onClick={() => cambiarEstado(c.id, "confirmada")}
                        className="rounded bg-green-600 px-2 py-0.5 text-xs text-white">Confirmar</button>
                    )}
                    {c.estado !== "cancelada" && (
                      <button onClick={() => cambiarEstado(c.id, "cancelada")}
                        className="rounded bg-red-500 px-2 py-0.5 text-xs text-white">Cancelar</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
