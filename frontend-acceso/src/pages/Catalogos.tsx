import { useEffect, useRef, useState } from "react";
import api from "../api/client";

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

type Tab = "grupos" | "tipos" | "protocolos";

// ── Tipos ──────────────────────────────────────────────────────────────────
interface Grupo    { id: number; nombre: string; descripcion: string; activo: boolean; }
interface Tipo     { id: number; grupo: number | null; grupo_nombre: string; nombre: string; descripcion: string; activo: boolean; }
interface Protocolo{ id: number; nombre: string; descripcion: string; archivo: string | null; estado: string; creado: string; }

// ── Helpers ────────────────────────────────────────────────────────────────
function Badge({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${ok ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-500"}`}>
      {ok ? "Activo" : "Inactivo"}
    </span>
  );
}
function inp(err?: string) {
  return `w-full rounded-xl border px-3 py-2 text-sm outline-none transition focus:ring-2 ${
    err ? "border-red-300 focus:ring-red-100" : "border-slate-200 focus:border-blue-400 focus:ring-blue-100"
  }`;
}
function Err({ msg }: { msg?: string }) {
  return msg ? <p className="mt-1 text-[11px] text-red-500">{msg}</p> : null;
}
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-bold" style={{ color: INK }}>{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:text-slate-700">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ── Grupos de documentos ──────────────────────────────────────────────────
function Grupos() {
  const [rows,    setRows]    = useState<Grupo[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState<"nuevo" | { id: number } | null>(null);
  const [form,    setForm]    = useState({ nombre: "", descripcion: "", activo: true });
  const [errs,    setErrs]    = useState<Record<string, string>>({});
  const [saving,  setSaving]  = useState(false);

  const cargar = () =>
    api.get("/api/grupos-documentos/").then(r => setRows(r.data.results ?? r.data)).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  function abrirNuevo() { setForm({ nombre: "", descripcion: "", activo: true }); setErrs({}); setModal("nuevo"); }
  function abrirEditar(g: Grupo) { setForm({ nombre: g.nombre, descripcion: g.descripcion ?? "", activo: g.activo }); setErrs({}); setModal({ id: g.id }); }

  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setErrs({});
    try {
      if (modal === "nuevo") await api.post("/api/grupos-documentos/", form);
      else await api.patch(`/api/grupos-documentos/${(modal as { id: number }).id}/`, form);
      setModal(null); cargar();
    } catch (err: any) {
      setErrs(err?.response?.data ?? { general: "Error al guardar." });
    } finally { setSaving(false); }
  }

  async function eliminar(id: number) {
    if (!confirm("¿Eliminar este grupo?")) return;
    try { await api.delete(`/api/grupos-documentos/${id}/`); cargar(); }
    catch { alert("No se pudo eliminar."); }
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-500">Agrupaciones lógicas de tipos de documentos.</p>
        <button onClick={abrirNuevo}
          className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white"
          style={{ backgroundColor: SIGNAL }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nuevo grupo
        </button>
      </div>
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? <div className="py-12 text-center"><div className="mx-auto h-7 w-7 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"/></div>
        : rows.length === 0 ? <p className="py-12 text-center text-sm text-slate-400">Sin grupos. Crea el primero.</p>
        : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Nombre</th>
                <th className="px-5 py-3">Descripción</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 w-20"/>
              </tr>
            </thead>
            <tbody>
              {rows.map(g => (
                <tr key={g.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                  <td className="px-5 py-3 font-medium text-slate-800">{g.nombre}</td>
                  <td className="px-5 py-3 text-slate-500 max-w-xs truncate">{g.descripcion || "—"}</td>
                  <td className="px-5 py-3"><Badge ok={g.activo}/></td>
                  <td className="px-5 py-3">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => abrirEditar(g)} className="rounded-lg p-1.5 text-slate-400 hover:bg-blue-50 hover:text-blue-600">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                      </button>
                      <button onClick={() => eliminar(g.id)} className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-500">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {modal && (
        <Modal title={modal === "nuevo" ? "Nuevo grupo" : "Editar grupo"} onClose={() => setModal(null)}>
          <form onSubmit={guardar} className="space-y-4">
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Nombre <span className="text-red-500">*</span></label>
              <input value={form.nombre} className={inp(errs.nombre)} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} />
              <Err msg={errs.nombre}/>
            </div>
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Descripción</label>
              <textarea value={form.descripcion} rows={3} className={inp()} onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))} />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="activo-g" checked={form.activo} onChange={e => setForm(f => ({ ...f, activo: e.target.checked }))} className="h-4 w-4 accent-blue-600"/>
              <label htmlFor="activo-g" className="text-sm text-slate-600">Activo</label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setModal(null)} className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={saving} className="rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: SIGNAL }}>
                {saving ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

// ── Tipos de documento ────────────────────────────────────────────────────
function Tipos() {
  const [rows,    setRows]    = useState<Tipo[]>([]);
  const [grupos,  setGrupos]  = useState<Grupo[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState<"nuevo" | { id: number } | null>(null);
  const [form,    setForm]    = useState({ nombre: "", descripcion: "", grupo: "", activo: true });
  const [errs,    setErrs]    = useState<Record<string, string>>({});
  const [saving,  setSaving]  = useState(false);

  const cargar = () =>
    Promise.all([
      api.get("/api/tipos-documento/"),
      api.get("/api/grupos-documentos/?activo=true"),
    ]).then(([t, g]) => {
      setRows(t.data.results ?? t.data);
      setGrupos(g.data.results ?? g.data);
    }).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  function abrirNuevo() { setForm({ nombre: "", descripcion: "", grupo: "", activo: true }); setErrs({}); setModal("nuevo"); }
  function abrirEditar(t: Tipo) {
    setForm({ nombre: t.nombre, descripcion: t.descripcion ?? "", grupo: String(t.grupo ?? ""), activo: t.activo });
    setErrs({}); setModal({ id: t.id });
  }

  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setErrs({});
    const payload = { ...form, grupo: form.grupo ? Number(form.grupo) : null };
    try {
      if (modal === "nuevo") await api.post("/api/tipos-documento/", payload);
      else await api.patch(`/api/tipos-documento/${(modal as { id: number }).id}/`, payload);
      setModal(null); cargar();
    } catch (err: any) { setErrs(err?.response?.data ?? {}); }
    finally { setSaving(false); }
  }

  async function eliminar(id: number) {
    if (!confirm("¿Eliminar este tipo de documento?")) return;
    try { await api.delete(`/api/tipos-documento/${id}/`); cargar(); }
    catch { alert("No se pudo eliminar."); }
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de documentos requeridos por grupo.</p>
        <button onClick={abrirNuevo} className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white" style={{ backgroundColor: SIGNAL }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nuevo tipo
        </button>
      </div>
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? <div className="py-12 text-center"><div className="mx-auto h-7 w-7 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"/></div>
        : rows.length === 0 ? <p className="py-12 text-center text-sm text-slate-400">Sin tipos de documento.</p>
        : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Nombre</th>
                <th className="px-5 py-3">Grupo</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 w-20"/>
              </tr>
            </thead>
            <tbody>
              {rows.map(t => (
                <tr key={t.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                  <td className="px-5 py-3 font-medium text-slate-800">{t.nombre}</td>
                  <td className="px-5 py-3 text-slate-500">{t.grupo_nombre || "—"}</td>
                  <td className="px-5 py-3"><Badge ok={t.activo}/></td>
                  <td className="px-5 py-3">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => abrirEditar(t)} className="rounded-lg p-1.5 text-slate-400 hover:bg-blue-50 hover:text-blue-600">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                      </button>
                      <button onClick={() => eliminar(t.id)} className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-500">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {modal && (
        <Modal title={modal === "nuevo" ? "Nuevo tipo de documento" : "Editar tipo"} onClose={() => setModal(null)}>
          <form onSubmit={guardar} className="space-y-4">
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Nombre <span className="text-red-500">*</span></label>
              <input value={form.nombre} className={inp(errs.nombre)} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}/>
              <Err msg={errs.nombre}/>
            </div>
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Grupo de documentos</label>
              <select value={form.grupo} className={inp()} onChange={e => setForm(f => ({ ...f, grupo: e.target.value }))}>
                <option value="">Sin grupo</option>
                {grupos.map(g => <option key={g.id} value={g.id}>{g.nombre}</option>)}
              </select>
            </div>
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Descripción</label>
              <input value={form.descripcion} className={inp()} onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}/>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="activo-t" checked={form.activo} onChange={e => setForm(f => ({ ...f, activo: e.target.checked }))} className="h-4 w-4 accent-blue-600"/>
              <label htmlFor="activo-t" className="text-sm text-slate-600">Activo</label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setModal(null)} className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={saving} className="rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: SIGNAL }}>
                {saving ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

// ── Protocolos ────────────────────────────────────────────────────────────
function Protocolos() {
  const [rows,    setRows]    = useState<Protocolo[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState<"nuevo" | { id: number } | null>(null);
  const [form,    setForm]    = useState({ nombre: "", descripcion: "", estado: "activo" });
  const [archivoFile, setArchivoFile] = useState<File | null>(null);
  const [errs,    setErrs]    = useState<Record<string, string>>({});
  const [saving,  setSaving]  = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const cargar = () =>
    api.get("/api/protocolos/").then(r => setRows(r.data.results ?? r.data)).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  function abrirNuevo() { setForm({ nombre: "", descripcion: "", estado: "activo" }); setArchivoFile(null); setErrs({}); setModal("nuevo"); }
  function abrirEditar(p: Protocolo) {
    setForm({ nombre: p.nombre, descripcion: p.descripcion ?? "", estado: p.estado });
    setArchivoFile(null); setErrs({}); setModal({ id: p.id });
  }

  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setErrs({});
    try {
      const fd = new FormData();
      fd.append("nombre",      form.nombre);
      fd.append("descripcion", form.descripcion);
      fd.append("estado",      form.estado);
      if (archivoFile) fd.append("archivo", archivoFile);
      if (modal === "nuevo") await api.post("/api/protocolos/", fd, { headers: { "Content-Type": "multipart/form-data" } });
      else await api.patch(`/api/protocolos/${(modal as { id: number }).id}/`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setModal(null); cargar();
    } catch (err: any) { setErrs(err?.response?.data ?? {}); }
    finally { setSaving(false); }
  }

  async function eliminar(id: number) {
    if (!confirm("¿Eliminar este protocolo?")) return;
    try { await api.delete(`/api/protocolos/${id}/`); cargar(); }
    catch { alert("No se pudo eliminar."); }
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-500">Documentos PDF descargables por los proveedores.</p>
        <button onClick={abrirNuevo} className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white" style={{ backgroundColor: SIGNAL }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nuevo protocolo
        </button>
      </div>
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? <div className="py-12 text-center"><div className="mx-auto h-7 w-7 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"/></div>
        : rows.length === 0 ? <p className="py-12 text-center text-sm text-slate-400">Sin protocolos registrados.</p>
        : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Nombre</th>
                <th className="px-5 py-3">Descripción</th>
                <th className="px-5 py-3">Archivo</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 w-20"/>
              </tr>
            </thead>
            <tbody>
              {rows.map(p => (
                <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                  <td className="px-5 py-3 font-medium text-slate-800">{p.nombre}</td>
                  <td className="px-5 py-3 text-slate-500 max-w-xs truncate">{p.descripcion || "—"}</td>
                  <td className="px-5 py-3">
                    {p.archivo ? (
                      <a href={p.archivo} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1 text-blue-600 hover:underline text-xs font-medium">
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path d="M12 16V8m0 8l-3-3m3 3l3-3M20 16.5A3.5 3.5 0 0016.5 13H15a5 5 0 10-9.9 1"/>
                        </svg>
                        Descargar
                      </a>
                    ) : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${p.estado === "activo" ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-500"}`}>
                      {p.estado === "activo" ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => abrirEditar(p)} className="rounded-lg p-1.5 text-slate-400 hover:bg-blue-50 hover:text-blue-600">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                      </button>
                      <button onClick={() => eliminar(p.id)} className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-500">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {modal && (
        <Modal title={modal === "nuevo" ? "Nuevo protocolo" : "Editar protocolo"} onClose={() => setModal(null)}>
          <form onSubmit={guardar} className="space-y-4">
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Nombre <span className="text-red-500">*</span></label>
              <input value={form.nombre} className={inp(errs.nombre)} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}/>
              <Err msg={errs.nombre}/>
            </div>
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Descripción</label>
              <textarea value={form.descripcion} rows={3} className={inp()} onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))}/>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Archivo (PDF / imagen)</label>
              <div
                role="button" tabIndex={0}
                onClick={() => fileRef.current?.click()}
                onKeyDown={e => e.key === "Enter" && fileRef.current?.click()}
                className={`flex cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed px-4 py-3 transition hover:border-blue-300 ${archivoFile ? "border-green-400 bg-green-50" : "border-slate-200 bg-slate-50"}`}
              >
                {archivoFile ? (
                  <><svg className="h-4 w-4 text-green-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>
                    <span className="text-xs font-medium text-green-700 truncate">{archivoFile.name}</span>
                  </>
                ) : (
                  <><svg className="h-4 w-4 text-slate-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                      <path d="M12 16V8m0 0l-3 3m3-3l3 3M20 16.5A3.5 3.5 0 0016.5 13H15a5 5 0 10-9.9 1M4 16.5A3.5 3.5 0 007.5 20h9"/>
                    </svg>
                    <span className="text-xs text-slate-400">Haz clic para seleccionar · PDF, JPG o PNG · máx. 20 MB</span>
                  </>
                )}
              </div>
              <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" onChange={e => setArchivoFile(e.target.files?.[0] ?? null)}/>
              <Err msg={errs.archivo}/>
            </div>
            <div><label className="block text-xs font-semibold text-slate-600 mb-1">Estado</label>
              <select value={form.estado} className={inp()} onChange={e => setForm(f => ({ ...f, estado: e.target.value }))}>
                <option value="activo">Activo</option>
                <option value="inactivo">Inactivo</option>
              </select>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setModal(null)} className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={saving} className="rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: SIGNAL }}>
                {saving ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

// ── Página principal ──────────────────────────────────────────────────────
const TABS: { id: Tab; label: string }[] = [
  { id: "grupos",     label: "Grupos de documentos" },
  { id: "tipos",      label: "Tipos de documento"  },
  { id: "protocolos", label: "Protocolos"           },
];

export default function Catalogos() {
  const [tab, setTab] = useState<Tab>("grupos");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Catálogos</h1>
        <p className="mt-0.5 text-sm text-slate-500">Configuración de grupos de documentos, tipos y protocolos del recinto.</p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-xl border border-slate-200 bg-white p-1 w-fit">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              tab === t.id
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "grupos"     && <Grupos/>}
      {tab === "tipos"      && <Tipos/>}
      {tab === "protocolos" && <Protocolos/>}
    </div>
  );
}
