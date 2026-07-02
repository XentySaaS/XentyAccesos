import { useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

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

const INK = "#0F1B2D";

const SEV_BADGE: Record<string, { bg: string; text: string }> = {
  bajo:  { bg: "bg-blue-100",   text: "text-blue-800"  },
  medio: { bg: "bg-amber-100",  text: "text-amber-800" },
  alto:  { bg: "bg-red-100",    text: "text-red-700"   },
};

const PEN_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  advertencia: { bg: "bg-amber-100",  text: "text-amber-800",  label: "Advertencia" },
  suspension:  { bg: "bg-orange-100", text: "text-orange-800", label: "Suspensión"  },
  baja:        { bg: "bg-red-100",    text: "text-red-700",    label: "Baja"        },
};

const FORM_INIT = {
  empleado: "", severidad: "bajo", penalidad: "advertencia",
  motivo: "", fecha_inicio: "", fecha_fin: "",
};

export default function Sanciones() {
  const [sanciones,  setSanciones]  = useState<Sancion[]>([]);
  const [empleados,  setEmpleados]  = useState<Empleado[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [showForm,   setShowForm]   = useState(false);
  const [form,       setForm]       = useState(FORM_INIT);
  const [saving,     setSaving]     = useState(false);
  const [error,      setError]      = useState("");

  const cargar = () =>
    Promise.all([
      api.get("/api/sanciones/"),
      api.get("/api/empleados/"),
    ]).then(([s, e]) => {
      setSanciones(s.data.results ?? s.data);
      setEmpleados(e.data.results ?? e.data);
    }).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await api.post("/api/sanciones/", {
        empleado: Number(form.empleado),
        severidad: form.severidad,
        penalidad: form.penalidad,
        motivo: form.motivo,
        fecha_inicio: form.penalidad === "suspension" ? form.fecha_inicio : null,
        fecha_fin:    form.penalidad === "suspension" ? form.fecha_fin    : null,
      });
      setShowForm(false); setForm(FORM_INIT); cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  const nombreEmpleado = (id: number) => empleados.find(e => e.id === id)?.nombre ?? `#${id}`;
  const F = form;
  const set = (k: keyof typeof FORM_INIT, v: string) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{ backgroundColor: "#FEF2F2" }}>
          <svg className="h-5 w-5 text-red-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Sanciones</h1>
          <p className="text-xs text-slate-500">Registro de advertencias y suspensiones</p>
        </div>
        <button onClick={() => { setError(""); setForm(FORM_INIT); setShowForm(true); }}
          className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: "#DC2626" }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nueva sanción
        </button>
      </div>

      {/* Tabla */}
      <div className="overflow-hidden rounded-card bg-white shadow-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left">
              {["Empleado", "Motivo", "Severidad", "Penalidad", "Período suspensión", "Fecha"].map(h => (
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
            {!loading && sanciones.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-400">
                Sin sanciones registradas.
              </td></tr>
            )}
            {!loading && sanciones.map(s => {
              const sev = SEV_BADGE[s.severidad ?? ""] ?? null;
              const pen = PEN_BADGE[s.penalidad ?? ""] ?? null;
              return (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold" style={{ color: INK }}>{nombreEmpleado(s.empleado)}</td>
                  <td className="max-w-xs truncate px-4 py-3 text-slate-500">{s.motivo}</td>
                  <td className="px-4 py-3">
                    {sev && (
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${sev.bg} ${sev.text}`}>
                        {s.severidad}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {pen && (
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${pen.bg} ${pen.text}`}>
                        {pen.label}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">
                    {s.fecha_inicio && s.fecha_fin ? `${s.fecha_inicio} → ${s.fecha_fin}` : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">
                    {new Date(s.creado).toLocaleDateString("es-MX")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Modal nueva sanción */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={crear} className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Nueva sanción</h2>
            <p className="mb-4 text-xs text-slate-400">Los campos marcados * son obligatorios.</p>

            {error && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}

            <div className="space-y-3">
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="san-empleado" className="text-xs font-semibold text-slate-600">Empleado *</label>
                  <Ayuda>Persona sancionada. La sanción bloquea su acceso en el escáner según la penalidad aplicada.</Ayuda>
                </div>
                <select id="san-empleado" required value={F.empleado} onChange={e => set("empleado", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                  <option value="">Seleccionar…</option>
                  {empleados.map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="san-severidad" className="text-xs font-semibold text-slate-600">Severidad</label>
                    <Ayuda>Gravedad de la falta (Bajo / Medio / Alto). Es informativa para el historial; no bloquea por sí sola el acceso — eso lo define la penalidad.</Ayuda>
                  </div>
                  <select id="san-severidad" value={F.severidad} onChange={e => set("severidad", e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    <option value="bajo">Bajo</option>
                    <option value="medio">Medio</option>
                    <option value="alto">Alto</option>
                  </select>
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="san-penalidad" className="text-xs font-semibold text-slate-600">Penalidad</label>
                    <Ayuda>Consecuencia aplicada. "Advertencia" no bloquea; "Suspensión" bloquea el acceso dentro del rango de fechas; "Baja" bloquea el acceso de forma permanente.</Ayuda>
                  </div>
                  <select id="san-penalidad" value={F.penalidad} onChange={e => set("penalidad", e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    <option value="advertencia">Advertencia</option>
                    <option value="suspension">Suspensión</option>
                    <option value="baja">Baja</option>
                  </select>
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="san-motivo" className="text-xs font-semibold text-slate-600">Motivo *</label>
                  <Ayuda>Descripción del incidente que origina la sanción. Queda registrada en el historial del empleado.</Ayuda>
                </div>
                <textarea id="san-motivo" required rows={3} value={F.motivo} onChange={e => set("motivo", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 resize-none"
                  placeholder="Describe el motivo de la sanción…" />
              </div>
              {F.penalidad === "suspension" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="san-fi" className="text-xs font-semibold text-slate-600">Fecha inicio *</label>
                      <Ayuda>Primer día de la suspensión. Desde esta fecha el escáner deniega el acceso del empleado.</Ayuda>
                    </div>
                    <input id="san-fi" required type="date" value={F.fecha_inicio} onChange={e => set("fecha_inicio", e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                  </div>
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="san-ff" className="text-xs font-semibold text-slate-600">Fecha fin *</label>
                      <Ayuda>Último día de la suspensión. Después de esta fecha el empleado recupera el acceso automáticamente.</Ayuda>
                    </div>
                    <input id="san-ff" required type="date" value={F.fecha_fin} onChange={e => set("fecha_fin", e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: "#DC2626" }}>
                {saving ? "Guardando…" : "Registrar sanción"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
