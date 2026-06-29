import { useEffect, useRef, useState } from "react";
import api from "../api/client";

interface TipoDocumento { id: number; nombre: string; }
interface Empleado { id: number; nombre: string; }
interface Documento {
  id: number;
  empleado: number;
  tipo_documento: number;
  tipo_archivo: string | null;
  estado: number;
  motivo_rechazo: string | null;
  creado: string;
}

const INK = "#0F1B2D";

const ESTADO_LABEL = ["Pendiente", "Verificado", "Rechazado"];
const ESTADO_BADGE = [
  "bg-amber-100 text-amber-700",
  "bg-green-100 text-green-800",
  "bg-red-100 text-red-700",
];

export default function Documentos() {
  const [docs, setDocs] = useState<Documento[]>([]);
  const [tipos, setTipos] = useState<TipoDocumento[]>([]);
  const [empleados, setEmpleados] = useState<Empleado[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ empleado: "", tipo_documento: "" });
  const [archivo, setArchivo] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const cargar = () =>
    Promise.all([
      api.get("/api/documentos-empleado/"),
      api.get("/api/tipos-documento/"),
      api.get("/api/empleados/"),
    ]).then(([d, t, e]) => {
      setDocs(d.data.results ?? d.data);
      setTipos(t.data.results ?? t.data);
      setEmpleados(e.data.results ?? e.data);
    }).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  const subir = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!archivo) { setError("Selecciona un archivo."); return; }
    setSaving(true); setError("");
    const fd = new FormData();
    fd.append("empleado", form.empleado);
    fd.append("tipo_documento", form.tipo_documento);
    fd.append("archivo", archivo);
    try {
      await api.post("/api/documentos-empleado/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setShowForm(false);
      setForm({ empleado: "", tipo_documento: "" });
      setArchivo(null);
      if (fileRef.current) fileRef.current.value = "";
      cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  const nombreEmpleado = (id: number) => empleados.find((e) => e.id === id)?.nombre ?? `#${id}`;
  const nombreTipo = (id: number) => tipos.find((t) => t.id === id)?.nombre ?? `#${id}`;

  const inputCls = "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

  return (
    <div>
      <div className="mb-6 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold" style={{ color: INK }}>Documentos</h1>
          <p className="mt-0.5 text-sm text-slate-500">Carga y seguimiento de documentos por empleado.</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="rounded-lg px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: "#2563EB" }}>
          Subir documento
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F1B2D]/40 p-4">
          <form onSubmit={subir} className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-4 text-base font-bold" style={{ color: INK }}>Subir documento</h2>
            {error && <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Empleado</label>
                <select required value={form.empleado} onChange={(e) => setForm({ ...form, empleado: e.target.value })} className={inputCls}>
                  <option value="">Seleccionar…</option>
                  {empleados.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Tipo de documento</label>
                <select required value={form.tipo_documento} onChange={(e) => setForm({ ...form, tipo_documento: e.target.value })} className={inputCls}>
                  <option value="">Seleccionar…</option>
                  {tipos.map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Archivo (PDF, JPG, PNG · máx. 10 MB)</label>
                <input ref={fileRef} required type="file" accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                  className="w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700" />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: "#2563EB" }}>
                {saving ? "Subiendo…" : "Subir"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          </div>
        ) : docs.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-slate-500">Aún no hay documentos. Sube el primero.</p>
            <p className="mt-1 text-xs text-slate-400">Carga los documentos requeridos para cada empleado.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Empleado</th>
                <th className="px-5 py-3">Tipo de documento</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3">Motivo de rechazo</th>
                <th className="px-5 py-3">Fecha subida</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-b border-slate-50 transition-colors hover:bg-slate-50/60">
                  <td className="px-5 py-3 font-medium text-slate-800">{nombreEmpleado(d.empleado)}</td>
                  <td className="px-5 py-3 text-slate-600">{nombreTipo(d.tipo_documento)}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${ESTADO_BADGE[d.estado] ?? "bg-slate-100 text-slate-600"}`}>
                      {ESTADO_LABEL[d.estado] ?? d.estado}
                    </span>
                  </td>
                  <td className="max-w-xs px-5 py-3 text-sm text-red-600">{d.motivo_rechazo ?? "—"}</td>
                  <td className="px-5 py-3 tabular text-slate-500">{new Date(d.creado).toLocaleDateString("es-MX")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
