import { useEffect, useRef, useState } from "react";
import api from "../api/client";

interface Empleado {
  id: number;
  nombre: string;
  email: string | null;
  telefono: string | null;
  estado: string;
}

interface DocEmpleado {
  id: number;
  tipo_documento: number;
  tipo_documento_nombre: string;
  archivo: string | null;
  tipo_archivo: string | null;
  estado: number; // 0=pendiente 1=verificado 2=rechazado
  motivo_rechazo: string | null;
  creado: string;
}

interface TipoDoc { id: number; nombre: string; }

const INK = "#0F1B2D";

const ESTADO_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  activo:   { bg: "bg-green-100", text: "text-green-800",  label: "Activo" },
  inactivo: { bg: "bg-slate-100", text: "text-slate-600",  label: "Inactivo" },
  baja:     { bg: "bg-red-100",   text: "text-red-700",    label: "Baja" },
};

const DOC_BADGE: Record<number, { label: string; cls: string }> = {
  0: { label: "Pendiente",  cls: "bg-amber-100 text-amber-800" },
  1: { label: "Verificado", cls: "bg-green-100 text-green-800" },
  2: { label: "Rechazado",  cls: "bg-red-100 text-red-700" },
};

const inputCls = "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

export default function Empleados() {
  const [empleados,    setEmpleados]    = useState<Empleado[]>([]);
  const [loading,      setLoading]      = useState(true);

  // ── Crear ──────────────────────────────────────────────────
  const [showForm,     setShowForm]     = useState(false);
  const [form,         setForm]         = useState({ nombre: "", email: "", telefono: "" });
  const [saving,       setSaving]       = useState(false);
  const [createError,  setCreateError]  = useState("");

  // ── Editar ─────────────────────────────────────────────────
  const [editModal,    setEditModal]    = useState<Empleado | null>(null);
  const [editForm,     setEditForm]     = useState({ email: "", telefono: "" });
  const [editSaving,   setEditSaving]   = useState(false);
  const [editError,    setEditError]    = useState("");

  // ── Documentos ─────────────────────────────────────────────
  const [docsModal,    setDocsModal]    = useState<Empleado | null>(null);
  const [docs,         setDocs]         = useState<DocEmpleado[]>([]);
  const [tipos,        setTipos]        = useState<TipoDoc[]>([]);
  const [loadingDocs,  setLoadingDocs]  = useState(false);
  const [tipoSel,      setTipoSel]      = useState<number | "">("");
  const [subiendo,     setSubiendo]     = useState(false);
  const [docsError,    setDocsError]    = useState("");
  const docFileRef = useRef<HTMLInputElement>(null);

  // ── Importar ───────────────────────────────────────────────
  const [importando,   setImportando]   = useState(false);
  const [importResult, setImportResult] = useState<{ creados: number; actualizados: number } | null>(null);
  const [globalError,  setGlobalError]  = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const cargar = () =>
    api.get("/api/empleados/")
      .then(r => setEmpleados(r.data.results ?? r.data))
      .catch(() => setGlobalError("No se pudieron cargar los empleados."))
      .finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  // ── Crear ──────────────────────────────────────────────────
  const crear = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setCreateError("");
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
      setCreateError(JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  // ── Editar ─────────────────────────────────────────────────
  function abrirEditar(emp: Empleado) {
    setEditModal(emp);
    setEditForm({ email: emp.email ?? "", telefono: emp.telefono ?? "" });
    setEditError("");
  }

  const guardarEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editModal) return;
    setEditSaving(true); setEditError("");
    try {
      await api.patch(`/api/empleados/${editModal.id}/`, {
        email: editForm.email || null,
        telefono: editForm.telefono || null,
      });
      setEditModal(null);
      cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setEditError(JSON.stringify(e.response?.data ?? "Error al guardar."));
    } finally { setEditSaving(false); }
  };

  // ── Estado ─────────────────────────────────────────────────
  const cambiarEstado = (id: number, estado: string) =>
    api.patch(`/api/empleados/${id}/`, { estado }).then(cargar);

  // ── Documentos ─────────────────────────────────────────────
  async function abrirDocs(emp: Empleado) {
    setDocsModal(emp); setDocs([]); setDocsError(""); setLoadingDocs(true); setTipoSel("");
    try {
      const [docsRes, tiposRes] = await Promise.all([
        api.get("/api/documentos-empleado/", { params: { empleado: emp.id } }),
        api.get("/api/tipos-documento/", { params: { activo: true } }),
      ]);
      setDocs(docsRes.data.results ?? docsRes.data);
      setTipos(tiposRes.data.results ?? tiposRes.data);
    } catch {
      setDocsError("No se pudieron cargar los documentos.");
    } finally { setLoadingDocs(false); }
  }

  async function subirDoc(file: File) {
    if (!tipoSel || !docsModal) { setDocsError("Elige el tipo de documento."); return; }
    setSubiendo(true); setDocsError("");
    const fd = new FormData();
    fd.append("empleado", String(docsModal.id));
    fd.append("tipo_documento", String(tipoSel));
    fd.append("archivo", file);
    try {
      await api.post("/api/documentos-empleado/", fd);
      setTipoSel("");
      if (docFileRef.current) docFileRef.current.value = "";
      await abrirDocs(docsModal);
    } catch (err: unknown) {
      const e = err as { response?: { data?: Record<string, string[]> } };
      const d = e.response?.data;
      setDocsError(d?.archivo?.[0] ?? d?.tipo_documento?.[0] ?? "No se pudo subir el documento.");
    } finally { setSubiendo(false); }
  }

  // ── Importar Excel ─────────────────────────────────────────
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
      setGlobalError("Error al importar. Verifica el formato del archivo.");
    } finally {
      setImportando(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

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
          <button onClick={() => { setShowForm(true); setCreateError(""); }}
            className="rounded-lg px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90"
            style={{ backgroundColor: "#2563EB" }}>
            Nuevo empleado
          </button>
        </div>
      </div>

      {globalError && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{globalError}</div>
      )}
      {importResult && (
        <div className="mb-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          Importación completada: <strong>{importResult.creados}</strong> creados,{" "}
          <strong>{importResult.actualizados}</strong> actualizados.
          <button className="ml-2 font-medium underline" onClick={() => setImportResult(null)}>Cerrar</button>
        </div>
      )}

      {/* ── Tabla ─────────────────────────────────────────────── */}
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
              {empleados.map(emp => {
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
                      <div className="flex flex-wrap justify-end gap-1.5">
                        <button onClick={() => abrirDocs(emp)}
                          className="rounded-lg border border-blue-200 px-2.5 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50">
                          Documentos
                        </button>
                        <button onClick={() => abrirEditar(emp)}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">
                          Editar
                        </button>
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

      {/* ── Modal: Nuevo empleado ──────────────────────────────── */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F1B2D]/40 p-4">
          <form onSubmit={crear} className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-4 text-base font-bold" style={{ color: INK }}>Nuevo empleado</h2>
            {createError && <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{createError}</p>}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Nombre completo</label>
                <input required value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })}
                  className={inputCls} placeholder="Juan García López" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Email</label>
                <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                  className={inputCls} placeholder="juan@empresa.com" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Teléfono</label>
                <input value={form.telefono} onChange={e => setForm({ ...form, telefono: e.target.value })}
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

      {/* ── Modal: Editar empleado ─────────────────────────────── */}
      {editModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F1B2D]/40 p-4">
          <form onSubmit={guardarEdit} className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Editar empleado</h2>
            <p className="mb-4 text-xs text-slate-500">{editModal.nombre}</p>
            {editError && <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{editError}</p>}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Email</label>
                <input type="email" value={editForm.email} onChange={e => setEditForm({ ...editForm, email: e.target.value })}
                  className={inputCls} placeholder="juan@empresa.com" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Teléfono</label>
                <input value={editForm.telefono} onChange={e => setEditForm({ ...editForm, telefono: e.target.value })}
                  className={inputCls} placeholder="55 1234 5678" />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setEditModal(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={editSaving}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: "#2563EB" }}>
                {editSaving ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal: Documentos del empleado ────────────────────── */}
      {docsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F1B2D]/40 p-4">
          <div className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-modal bg-white shadow-panel">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-slate-100 px-6 py-4">
              <div>
                <h2 className="text-base font-bold" style={{ color: INK }}>Documentos</h2>
                <p className="text-xs text-slate-500">{docsModal.nombre}</p>
              </div>
              <button onClick={() => setDocsModal(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {docsError && (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{docsError}</p>
              )}

              {/* Lista de documentos existentes */}
              {loadingDocs ? (
                <div className="flex justify-center py-8">
                  <div className="h-7 w-7 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
                </div>
              ) : docs.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-400">Sin documentos subidos aún.</p>
              ) : (
                <div className="space-y-2">
                  {docs.map(d => {
                    const b = DOC_BADGE[d.estado] ?? { label: String(d.estado), cls: "bg-slate-100 text-slate-700" };
                    return (
                      <div key={d.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2.5">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-slate-700">{d.tipo_documento_nombre}</p>
                          {d.motivo_rechazo && (
                            <p className="truncate text-xs text-red-600">Motivo: {d.motivo_rechazo}</p>
                          )}
                          <p className="font-mono text-[10px] text-slate-400">
                            {new Date(d.creado).toLocaleDateString("es-MX")}
                            {d.tipo_archivo && <span className="ml-1.5 uppercase">{d.tipo_archivo}</span>}
                          </p>
                        </div>
                        <span className={`ml-3 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${b.cls}`}>
                          {b.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Subir nuevo documento */}
              {!loadingDocs && tipos.length > 0 && (
                <div className="border-t border-slate-100 pt-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Subir documento</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={tipoSel}
                      onChange={e => { setTipoSel(e.target.value ? Number(e.target.value) : ""); setDocsError(""); }}
                      className="h-9 flex-1 rounded-lg border border-slate-200 px-2 text-sm">
                      <option value="">Tipo de documento…</option>
                      {tipos.map(t => <option key={t.id} value={t.id}>{t.nombre}</option>)}
                    </select>
                    <label className={`cursor-pointer rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 ${subiendo ? "opacity-50 pointer-events-none" : ""}`}>
                      {subiendo ? "Subiendo…" : "Elegir archivo"}
                      <input ref={docFileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
                        onChange={e => { const f = e.target.files?.[0]; if (f) subirDoc(f); }} />
                    </label>
                  </div>
                  <p className="mt-1.5 text-[11px] text-slate-400">PDF, JPG o PNG · máx. 2 MB · se envía a verificación del recinto.</p>
                </div>
              )}
            </div>

            <div className="flex justify-end border-t border-slate-100 px-6 py-4">
              <button onClick={() => setDocsModal(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
