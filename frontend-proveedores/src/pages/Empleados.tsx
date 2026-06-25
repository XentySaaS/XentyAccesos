import { useEffect, useRef, useState } from "react";
import api from "../api/client";

interface Empleado {
  id: number;
  nombre: string;
  email: string | null;
  telefono: string | null;
  estado: string;
}

const ESTADO_COLOR: Record<string, string> = {
  activo: "bg-green-100 text-green-800",
  inactivo: "bg-slate-100 text-slate-600",
  baja: "bg-red-100 text-red-800",
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
    api.get("/api/empleados/empleados/")
      .then((r) => setEmpleados(r.data.results ?? r.data))
      .finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      await api.post("/api/empleados/empleados/", {
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
    api.patch(`/api/empleados/empleados/${id}/`, { estado }).then(cargar);

  const importarXlsx = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportando(true); setImportResult(null);
    const fd = new FormData();
    fd.append("archivo", file);
    try {
      const r = await api.post("/api/empleados/empleados/importar/", fd, {
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

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Empleados</h1>
        <div className="ml-auto flex gap-2">
          <label className={`cursor-pointer rounded border px-3 py-1 text-sm ${importando ? "opacity-50" : "hover:bg-slate-50"}`}>
            {importando ? "Importando…" : "Importar Excel"}
            <input ref={fileRef} type="file" accept=".xlsx" className="hidden" onChange={importarXlsx} />
          </label>
          <button onClick={() => setShowForm(true)}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">
            + Nuevo empleado
          </button>
        </div>
      </div>

      {importResult && (
        <div className="mb-3 rounded bg-green-50 p-3 text-sm text-green-800">
          Importación completada: <strong>{importResult.creados}</strong> creados,{" "}
          <strong>{importResult.actualizados}</strong> actualizados.
          <button className="ml-2 underline" onClick={() => setImportResult(null)}>Cerrar</button>
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <form onSubmit={crear} className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Nuevo empleado</h2>
            {error && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Nombre completo</label>
                <input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" placeholder="Juan García López" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Email</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" placeholder="juan@empresa.com" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Teléfono</label>
                <input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm" placeholder="55 1234 5678" />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded border px-4 py-1 text-sm">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded bg-blue-600 px-4 py-1 text-sm text-white disabled:opacity-50">
                {saving ? "Guardando…" : "Crear"}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-slate-500">Cargando…</p>
      ) : empleados.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center text-slate-400 shadow-sm">
          <p className="mb-2">No hay empleados registrados.</p>
          <p className="text-xs">Agrega empleados manualmente o importa un archivo Excel (.xlsx)</p>
          <p className="mt-1 text-xs text-slate-300">Columnas requeridas: nombre, email, teléfono</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b bg-slate-50 text-xs text-slate-500">
              <tr>
                {["Nombre", "Email", "Teléfono", "Estado", "Acciones"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {empleados.map((emp) => (
                <tr key={emp.id} className="border-b hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{emp.nombre}</td>
                  <td className="px-4 py-2 text-slate-600">{emp.email ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-600">{emp.telefono ?? "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_COLOR[emp.estado] ?? "bg-slate-100"}`}>
                      {emp.estado}
                    </span>
                  </td>
                  <td className="flex gap-1 px-4 py-2">
                    {emp.estado === "activo" && (
                      <button onClick={() => cambiarEstado(emp.id, "inactivo")}
                        className="rounded border px-2 py-0.5 text-xs hover:bg-slate-50">Desactivar</button>
                    )}
                    {emp.estado === "inactivo" && (
                      <button onClick={() => cambiarEstado(emp.id, "activo")}
                        className="rounded bg-green-600 px-2 py-0.5 text-xs text-white">Activar</button>
                    )}
                    {emp.estado !== "baja" && (
                      <button onClick={() => cambiarEstado(emp.id, "baja")}
                        className="rounded bg-red-500 px-2 py-0.5 text-xs text-white">Dar de baja</button>
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
