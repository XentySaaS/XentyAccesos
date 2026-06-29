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

interface Recinto  { id: number; nombre: string; }
interface Proveedor { id: number; nombre: string; }

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const TIPO_CITA_LABEL: Record<string, string> = {
  programada: "Programada", walk_in: "Walk-in", emergencia: "Emergencia",
};

const ESTADO_BADGE: Record<string, { bg: string; text: string }> = {
  pendiente:  { bg: "bg-amber-100",  text: "text-amber-800"  },
  confirmada: { bg: "bg-green-100",  text: "text-green-800"  },
  cancelada:  { bg: "bg-red-100",    text: "text-red-700"    },
};

type ModalMode = "crear" | null;

const FORM_INIT = {
  nombre: "", fecha: "", hora_inicio: "", hora_fin: "",
  tipo: 0, tipo_cita: "programada", recinto: "", proveedor: "", limite: "",
};

export default function Citas() {
  const [citas,       setCitas]       = useState<Cita[]>([]);
  const [recintos,    setRecintos]    = useState<Recinto[]>([]);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [modal,       setModal]       = useState<ModalMode>(null);
  const [filtroEstado,setFiltroEstado]= useState("");
  const [form,        setForm]        = useState(FORM_INIT);
  const [saving,      setSaving]      = useState(false);
  const [error,       setError]       = useState("");

  const cargar = () => {
    const params: Record<string, string> = {};
    if (filtroEstado) params.estado = filtroEstado;
    return Promise.all([
      api.get("/api/citas/", { params }),
      api.get("/api/recintos/"),
      api.get("/api/proveedores/"),
    ]).then(([c, r, p]) => {
      setCitas(c.data.results ?? c.data);
      setRecintos(r.data.results ?? r.data);
      setProveedores(p.data.results ?? p.data);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [filtroEstado]);

  const cambiarEstado = (id: number, estado: string) =>
    api.patch(`/api/citas/${id}/`, { estado }).then(cargar);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await api.post("/api/citas/", {
        nombre: form.nombre, fecha: form.fecha,
        hora_inicio: form.hora_inicio || null, hora_fin: form.hora_fin || null,
        tipo: Number(form.tipo), tipo_cita: form.tipo_cita, estado: "pendiente",
        recinto: Number(form.recinto),
        proveedor: form.proveedor ? Number(form.proveedor) : null,
        limite: form.limite ? Number(form.limite) : null,
      });
      setModal(null); setForm(FORM_INIT); cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error al crear la cita."));
    } finally { setSaving(false); }
  };

  const F = form;
  const set = (k: keyof typeof FORM_INIT, v: string | number) =>
    setForm(f => ({ ...f, [k]: v }));

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{ backgroundColor: "#EFF6FF" }}>
          <svg className="h-5 w-5" style={{ color: SIGNAL }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Citas</h1>
          <p className="text-xs text-slate-500">Agenda de visitas y accesos programados</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={filtroEstado} onChange={e => setFiltroEstado(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendiente</option>
            <option value="confirmada">Confirmada</option>
            <option value="cancelada">Cancelada</option>
          </select>
          <button onClick={() => { setError(""); setForm(FORM_INIT); setModal("crear"); }}
            className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white"
            style={{ backgroundColor: SIGNAL }}>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
            Nueva cita
          </button>
        </div>
      </div>

      {/* Tabla */}
      <div className="overflow-hidden rounded-card bg-white shadow-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left">
              {["Nombre / motivo", "Fecha", "Horario", "Tipo", "Estado", "Acciones"].map(h => (
                <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading && (
              <tr><td colSpan={6} className="px-4 py-8">
                <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />)}</div>
              </td></tr>
            )}
            {!loading && citas.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-400">Sin citas registradas.</td></tr>
            )}
            {!loading && citas.map(c => {
              const badge = ESTADO_BADGE[c.estado] ?? { bg: "bg-slate-100", text: "text-slate-600" };
              return (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold" style={{ color: INK }}>{c.nombre || `Cita #${c.id}`}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{c.fecha ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">
                    {c.hora_inicio && c.hora_fin
                      ? `${c.hora_inicio.slice(0, 5)} – ${c.hora_fin.slice(0, 5)}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{TIPO_CITA_LABEL[c.tipo_cita] ?? c.tipo_cita}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.bg} ${badge.text}`}>
                      {c.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1.5">
                      {c.estado === "pendiente" && (
                        <button onClick={() => cambiarEstado(c.id, "confirmada")}
                          className="rounded-lg px-2 py-1 text-xs font-semibold text-white"
                          style={{ backgroundColor: "#16A34A" }}>
                          Confirmar
                        </button>
                      )}
                      {c.estado !== "cancelada" && (
                        <button onClick={() => cambiarEstado(c.id, "cancelada")}
                          className="rounded-lg border px-2 py-1 text-xs font-semibold"
                          style={{ borderColor: "#DC2626", color: "#DC2626" }}>
                          Cancelar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Modal nueva cita */}
      {modal === "crear" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={crear} className="w-full max-w-lg rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Nueva cita</h2>
            <p className="mb-4 text-xs text-slate-400">Los campos marcados * son obligatorios.</p>

            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="mb-1 block text-xs font-semibold text-slate-600">Nombre / motivo *</label>
                <input required value={F.nombre} onChange={e => set("nombre", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  placeholder="Reunión de proveedores…" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Fecha *</label>
                <input required type="date" value={F.fecha} onChange={e => set("fecha", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Límite asistentes</label>
                <input type="number" min="1" value={F.limite} onChange={e => set("limite", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  placeholder="Sin límite" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Hora inicio</label>
                <input type="time" value={F.hora_inicio} onChange={e => set("hora_inicio", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Hora fin</label>
                <input type="time" value={F.hora_fin} onChange={e => set("hora_fin", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Tipo de cita</label>
                <select value={F.tipo_cita} onChange={e => set("tipo_cita", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                  <option value="programada">Programada</option>
                  <option value="walk_in">Walk-in</option>
                  <option value="emergencia">Emergencia</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Tipo</label>
                <select value={F.tipo} onChange={e => set("tipo", Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                  <option value={0}>Proveedor</option>
                  <option value={1}>Directa</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Recinto *</label>
                <select required value={F.recinto} onChange={e => set("recinto", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                  <option value="">Seleccionar…</option>
                  {recintos.map(r => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Proveedor</label>
                <select value={F.proveedor} onChange={e => set("proveedor", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                  <option value="">Sin proveedor</option>
                  {proveedores.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: SIGNAL }}>
                {saving ? "Creando…" : "Crear cita"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
