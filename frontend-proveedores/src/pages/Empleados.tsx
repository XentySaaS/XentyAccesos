import { useEffect, useRef, useState } from "react";
import api from "../api/client";

interface Empleado {
  id: number;
  nombre: string;
  email: string | null;
  telefono: string | null;
  estado: string;
}

const INK = "#0F1B2D";

const ESTADO_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  activo:   { bg: "bg-green-100", text: "text-green-800",  label: "Activo" },
  inactivo: { bg: "bg-slate-100", text: "text-slate-600",  label: "Inactivo" },
  baja:     { bg: "bg-red-100",   text: "text-red-700",    label: "Baja" },
};

export default function Empleados() {
  const [empleados, setEmpleados] = useState<Empleado[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nombre: "", email: "", telefono: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [importando, setImportando] = useState(false);
  const [importResult, setImportResult] = useState<{ creados: number; actualizados: number } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const cargar = () =>
    api.get("/api/empleados/")
      .then((r) => setEmpleados(r.data.results ?? r.data))
      .finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      await api.post("/api/empleados/", {
        nombre: form.nombre,
        email: form.email || null,
        telefono: form.telefono || null,
      });
      setShowForm(false);
      setForm({ nombre: "", email: "", telefono: "" });
      cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  const cambiarEstado = (id: number, estado: string) =>
    api.patch(`/api/empleados/${id}/`, { estado }).then(cargar);

  const importarXlsx = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportando(true); setImportResult(null);
    const fd = new FormData();
    fd.append("archivo", file);
    try {
      const r = await api.post("/api/empleados/importar/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult(r.data);
      cargar();
    } catch {
      setError("Error al importar. Verifica el formato del archivo.");
    } finally {
      setImportando(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const inputCls = "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold" style={{ color: INK }}>Empleados</h1>
          <p className="mt-0.5 text-sm text-slate-500">Plantilla de tu empresa para asignar a eventos.</p>
        </div>
        <div className="flex gap-2">
          <label className={`cursor-pointer rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 ${importando ? "opacity-50" : ""}`}>
            {importando ? "Importando…" : "Importar Excel"}
            <input ref={fileRef} type="file" accept=".xlsx" className="hidden" onChange={importarXlsx} />
          </label>
          <button onClick={() => setShowForm(true)}
            className="rounded-lg px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90"
            style={{ backgroundColor: "#2563EB" }}>
            Nuevo empleado
          </button>
        </div>
      </div>

      {importResult && (
        <div className="mb-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          Importación completada: <strong>{importResult.creados}</strong> creados,{" "}
          <strong>{importResult.actualizados}</strong> actualizados.
          <button className="ml-2 font-medium underline" onClick={() => setImportResult(null)}>Cerrar</button>
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F1B2D]/40 p-4">
          <form onSubmit={crear} className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-4 text-base font-bold" style={{ color: INK }}>Nuevo empleado</h2>
            {error && <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Nombre completo</label>
                <input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  className={inputCls} placeholder="Juan García López" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Email</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className={inputCls} placeholder="juan@empresa.com" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Teléfono</label>
                <input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                  className={inputCls} placeholder="55 1234 5678" />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: "#2563EB" }}>
                {saving ? "Guardando…" : "Crear"}
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
        ) : empleados.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-slate-500">Aún no hay empleados. Agrega el primero.</p>
            <p className="mt-1 text-xs text-slate-400">Manualmente o importando un Excel (.xlsx) con columnas: nombre, email, teléfono.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Nombre</th>
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">Teléfono</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {empleados.map((emp) => {
                const b = ESTADO_BADGE[emp.estado] ?? { bg: "bg-slate-100", text: "text-slate-700", label: emp.estado };
                return (
                  <tr key={emp.id} className="border-b border-slate-50 transition-colors hover:bg-slate-50/60">
                    <td className="px-5 py-3 font-medium text-slate-800">{emp.nombre}</td>
                    <td className="px-5 py-3 text-slate-600">{emp.email ?? "—"}</td>
                    <td className="px-5 py-3 tabular text-slate-600">{emp.telefono ?? "—"}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${b.bg} ${b.text}`}>{b.label}</span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-1.5">
                        {emp.estado === "activo" && (
                          <button onClick={() => cambiarEstado(emp.id, "inactivo")}
                            className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">Desactivar</button>
                        )}
                        {emp.estado === "inactivo" && (
                          <button onClick={() => cambiarEstado(emp.id, "activo")}
                            className="rounded-lg bg-[#16A34A] px-2.5 py-1 text-xs font-medium text-white hover:opacity-90">Activar</button>
                        )}
                        {emp.estado !== "baja" && (
                          <button onClick={() => cambiarEstado(emp.id, "baja")}
                            className="rounded-lg border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50">Dar de baja</button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
