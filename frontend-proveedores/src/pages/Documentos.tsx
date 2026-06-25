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

const ESTADO_LABEL = ["Pendiente", "Verificado", "Rechazado"];
const ESTADO_COLOR = [
  "bg-yellow-100 text-yellow-800",
  "bg-green-100 text-green-800",
  "bg-red-100 text-red-800",
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
      api.get("/api/documentos/documentos-empleado/"),
      api.get("/api/documentos/tipos-documento/"),
      api.get("/api/empleados/empleados/"),
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
      await api.post("/api/documentos/documentos-empleado/", fd, {
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

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Documentos</h1>
        <button onClick={() => setShowForm(true)}
          className="ml-auto rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">
          + Subir documento
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <form onSubmit={subir} className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Subir documento</h2>
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
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Tipo de documento</label>
                <select required value={form.tipo_documento} onChange={(e) => setForm({ ...form, tipo_documento: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm">
                  <option value="">Seleccionar…</option>
                  {tipos.map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Archivo (PDF, JPG, PNG · máx. 10 MB)</label>
                <input ref={fileRef} required type="file" accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                  className="w-full text-sm" />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded border px-4 py-1 text-sm">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded bg-blue-600 px-4 py-1 text-sm text-white disabled:opacity-50">
                {saving ? "Subiendo…" : "Subir"}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-slate-500">Cargando…</p>
      ) : docs.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center text-slate-400 shadow-sm">
          <p>No hay documentos subidos aún.</p>
          <p className="mt-1 text-xs">Sube los documentos requeridos para cada empleado.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b bg-slate-50 text-xs text-slate-500">
              <tr>
                {["Empleado", "Tipo de documento", "Estado", "Motivo de rechazo", "Fecha subida"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-b hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{nombreEmpleado(d.empleado)}</td>
                  <td className="px-4 py-2 text-slate-600">{nombreTipo(d.tipo_documento)}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_COLOR[d.estado] ?? "bg-slate-100"}`}>
                      {ESTADO_LABEL[d.estado] ?? d.estado}
                    </span>
                  </td>
                  <td className="max-w-xs px-4 py-2 text-sm text-red-600">{d.motivo_rechazo ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-500">{new Date(d.creado).toLocaleDateString("es-MX")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
