import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

/* ── Tipos ──────────────────────────────────────────────────────────────── */
interface Recinto {
  id: number; nombre: string | null; codigo: string | null;
  telefono: string | null; descripcion: string | null;
}
interface SubItem { id: number; nombre: string; descripcion: string | null; activo?: boolean; }
interface Ubicacion { id: number; nombre: string; descripcion: string | null; }

type SubTab = "zonas" | "accesos" | "areas";

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const TAB_META: Record<SubTab, { label: string; endpoint: string; placeholder: string }> = {
  zonas:   { label: "Zonas",             endpoint: "/api/zonas/",             placeholder: "Ej. Zona Norte, Patio Central…"   },
  accesos: { label: "Puntos de acceso",  endpoint: "/api/accesos/",           placeholder: "Ej. Entrada principal, Portón 3…" },
  areas:   { label: "Áreas autorizadas", endpoint: "/api/areas-autorizadas/", placeholder: "Ej. Almacén, Sala de reuniones…"   },
};

/* ══════════════════════════════════════════════════════════════════════════
   Página principal
   ══════════════════════════════════════════════════════════════════════════ */
export default function Recintos() {
  const [items,   setItems]   = useState<Recinto[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState<"crear" | "editar" | null>(null);
  const [gestion, setGestion] = useState<Recinto | null>(null);
  const [sel,     setSel]     = useState<Recinto | null>(null);
  const [error,   setError]   = useState<string | null>(null);
  const [saving,  setSaving]  = useState(false);

  const [nombre,     setNombre]     = useState("");
  const [codigo,     setCodigo]     = useState("");
  const [telefono,   setTelefono]   = useState("");
  const [descripcion,setDescripcion]= useState("");

  async function cargar() {
    setLoading(true);
    try {
      const { data } = await api.get("/api/recintos/");
      setItems(Array.isArray(data) ? data : data.results ?? []);
    } finally { setLoading(false); }
  }
  useEffect(() => { cargar(); }, []);

  function abrirCrear() {
    setNombre(""); setCodigo(""); setTelefono(""); setDescripcion("");
    setError(null); setModal("crear");
  }
  function abrirEditar(r: Recinto) {
    setSel(r);
    setNombre(r.nombre ?? ""); setCodigo(r.codigo ?? "");
    setTelefono(r.telefono ?? ""); setDescripcion(r.descripcion ?? "");
    setError(null); setModal("editar");
  }

  async function guardar(e: FormEvent) {
    e.preventDefault(); setSaving(true); setError(null);
    try {
      const payload = { nombre: nombre || null, codigo: codigo || null,
        telefono: telefono || null, descripcion: descripcion || null };
      if (modal === "editar" && sel) await api.patch(`/api/recintos/${sel.id}/`, payload);
      else await api.post("/api/recintos/", payload);
      setModal(null); await cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail ?? "No se pudo guardar.");
    } finally { setSaving(false); }
  }

  const inputCls = "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100";

  return (
    <div>
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
          <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Recintos</h1>
          <p className="text-xs text-slate-500">Sedes, zonas, puntos de acceso y áreas autorizadas</p>
        </div>
        <button onClick={abrirCrear}
          className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: SIGNAL }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nuevo recinto
        </button>
      </div>

      {/* ── Tabla ─────────────────────────────────────────────── */}
      <div className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 text-left">
              {["Nombre", "Código", "Teléfono", "Acciones"].map(h => (
                <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading && (
              <tr><td colSpan={4} className="px-4 py-8">
                <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />)}</div>
              </td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-10 text-center text-sm text-slate-400">
                Sin recintos. Crea el primero.
              </td></tr>
            )}
            {!loading && items.map(r => (
              <tr key={r.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <p className="font-semibold" style={{ color: INK }}>{r.nombre ?? "—"}</p>
                  {r.descripcion && <p className="text-xs text-slate-400 truncate max-w-xs">{r.descripcion}</p>}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.codigo ?? "—"}</td>
                <td className="px-4 py-3 text-slate-500">{r.telefono ?? "—"}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button onClick={() => abrirEditar(r)}
                      className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">
                      Editar
                    </button>
                    <button onClick={() => setGestion(r)}
                      className="rounded-lg px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90"
                      style={{ backgroundColor: SIGNAL }}>
                      Gestionar →
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Modal crear / editar recinto ──────────────────────── */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={guardar}
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>
              {modal === "crear" ? "Nuevo recinto" : "Editar recinto"}
            </h2>
            <p className="mb-4 text-xs text-slate-400">Los campos marcados * son obligatorios.</p>
            {error && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}
            <div className="space-y-3">
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="rec-nombre" className="text-xs font-semibold text-slate-600">Nombre *</label>
                  <Ayuda>Nombre del inmueble (estadio, centro de convenciones, etc.). Es la sede que agrupa zonas, puntos de acceso y áreas autorizadas.</Ayuda>
                </div>
                <input id="rec-nombre" required value={nombre} onChange={e => setNombre(e.target.value)} className={inputCls} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="rec-codigo" className="text-xs font-semibold text-slate-600">Código</label>
                    <Ayuda>Clave corta interna para identificar el recinto en reportes (p. ej. REC-01). Opcional.</Ayuda>
                  </div>
                  <input id="rec-codigo" value={codigo} onChange={e => setCodigo(e.target.value)} placeholder="REC-01" className={inputCls} />
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="rec-tel" className="text-xs font-semibold text-slate-600">Teléfono</label>
                    <Ayuda>Teléfono de contacto del recinto (opcional). 10 dígitos, sin lada. Ej. 5512345678</Ayuda>
                  </div>
                  <input id="rec-tel" value={telefono} onChange={e => setTelefono(e.target.value.replace(/\D/g, "").slice(0, 10))} placeholder="5512345678" maxLength={10} inputMode="numeric" className={inputCls} />
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="rec-desc" className="text-xs font-semibold text-slate-600">Descripción</label>
                  <Ayuda>Notas internas sobre el recinto (ubicación, referencias). No se muestra en gafetes.</Ayuda>
                </div>
                <textarea id="rec-desc" rows={2} value={descripcion} onChange={e => setDescripcion(e.target.value)}
                  className="w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
                style={{ backgroundColor: SIGNAL }}>
                {saving ? "Guardando…" : modal === "crear" ? "Crear recinto" : "Guardar cambios"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal gestionar sub-entidades ─────────────────────── */}
      {gestion && <GestionModal recinto={gestion} onClose={() => setGestion(null)} />}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════
   Modal de gestión
   ══════════════════════════════════════════════════════════════════════════ */
function GestionModal({ recinto, onClose }: { recinto: { id: number; nombre: string | null }; onClose: () => void }) {
  const [tab,     setTab]    = useState<SubTab>("zonas");
  const [items,   setItems]  = useState<SubItem[]>([]);
  const [loading, setLoading]= useState(true);
  const [nombre,  setNombre] = useState("");
  const [desc,    setDesc]   = useState("");
  const [saving,  setSaving] = useState(false);
  const [error,   setError]  = useState("");
  const [deleting,setDeleting]=useState<number | null>(null);

  /* — Ubicaciones por zona — */
  const [expandedZona, setExpandedZona]     = useState<number | null>(null);
  const [zonaUbics,    setZonaUbics]        = useState<Record<number, Ubicacion[]>>({});
  const [loadingUbic,  setLoadingUbic]      = useState<number | null>(null);
  const [newUbicName,  setNewUbicName]      = useState<Record<number, string>>({});
  const [newUbicDesc,  setNewUbicDesc]      = useState<Record<number, string>>({});
  const [savingUbic,   setSavingUbic]       = useState<number | null>(null);
  const [deletingUbic, setDeletingUbic]     = useState<number | null>(null);

  const meta = TAB_META[tab];

  async function cargarSub() {
    setLoading(true); setItems([]);
    try {
      const { data } = await api.get(meta.endpoint, { params: { recinto: recinto.id } });
      setItems(Array.isArray(data) ? data : data.results ?? []);
    } finally { setLoading(false); }
  }

  useEffect(() => {
    setNombre(""); setDesc(""); setError("");
    setExpandedZona(null);
    cargarSub();
  }, [tab]);

  async function crear(e: FormEvent) {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await api.post(meta.endpoint, { nombre, descripcion: desc || null, recinto: recinto.id });
      setNombre(""); setDesc(""); await cargarSub();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string; nombre?: string[] } } };
      setError(e?.response?.data?.detail ?? e?.response?.data?.nombre?.[0] ?? "No se pudo crear.");
    } finally { setSaving(false); }
  }

  async function eliminar(id: number) {
    if (!confirm("¿Eliminar este elemento?")) return;
    setDeleting(id);
    try { await api.delete(`${meta.endpoint}${id}/`); await cargarSub(); }
    finally { setDeleting(null); }
  }

  /* ── Ubicaciones ──────────────────────────────────────────── */
  async function cargarUbicaciones(zonaId: number) {
    setLoadingUbic(zonaId);
    try {
      const { data } = await api.get("/api/ubicaciones/", { params: { zona: zonaId } });
      setZonaUbics(prev => ({ ...prev, [zonaId]: Array.isArray(data) ? data : data.results ?? [] }));
    } finally { setLoadingUbic(null); }
  }

  async function toggleZona(zonaId: number) {
    if (expandedZona === zonaId) { setExpandedZona(null); return; }
    setExpandedZona(zonaId);
    await cargarUbicaciones(zonaId);
  }

  async function crearUbicacion(e: FormEvent, zonaId: number) {
    e.preventDefault();
    const nombre = (newUbicName[zonaId] ?? "").trim();
    if (!nombre) return;
    setSavingUbic(zonaId);
    try {
      await api.post("/api/ubicaciones/", {
        nombre,
        descripcion: (newUbicDesc[zonaId] ?? "") || null,
        zona: zonaId,
      });
      setNewUbicName(p => ({ ...p, [zonaId]: "" }));
      setNewUbicDesc(p => ({ ...p, [zonaId]: "" }));
      await cargarUbicaciones(zonaId);
    } finally { setSavingUbic(null); }
  }

  async function eliminarUbicacion(id: number, zonaId: number) {
    if (!confirm("¿Eliminar esta ubicación?")) return;
    setDeletingUbic(id);
    try { await api.delete(`/api/ubicaciones/${id}/`); await cargarUbicaciones(zonaId); }
    finally { setDeletingUbic(null); }
  }

  /* ── Render ───────────────────────────────────────────────── */
  const tabs: SubTab[] = ["zonas", "accesos", "areas"];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
      <div className="flex w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        style={{ maxHeight: "88vh" }}>

        {/* ── Cabecera ──────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-blue-50">
              <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-bold" style={{ color: INK }}>
                {recinto.nombre ?? "Recinto"}
              </h2>
              <p className="text-xs text-slate-400">Zonas, accesos y áreas autorizadas</p>
            </div>
          </div>
          <button onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* ── Tabs ──────────────────────────────────────────── */}
        <div className="flex gap-1 border-b border-slate-100 bg-slate-50 px-5 pt-3">
          {tabs.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`rounded-t-lg px-4 py-2.5 text-xs font-semibold transition-colors ${
                tab === t
                  ? "border-b-2 border-blue-500 bg-white text-blue-600"
                  : "text-slate-400 hover:text-slate-600"
              }`}>
              {TAB_META[t].label}
              {tab === t && items.length > 0 && (
                <span className="ml-1.5 rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-bold text-blue-600">
                  {items.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── Lista ─────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="space-y-2 p-5">
              {[1,2,3].map(i => <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-100" />)}
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-14 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
                <svg className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                  <path d="M12 9v3m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </div>
              <p className="text-sm font-medium text-slate-500">Sin {TAB_META[tab].label.toLowerCase()}</p>
              <p className="mt-0.5 text-xs text-slate-400">Agrega el primero desde el formulario de abajo.</p>
            </div>
          ) : tab === "zonas" ? (
            /* ── Zonas: lista expandible con ubicaciones ───── */
            <div className="divide-y divide-slate-100">
              {items.map(zona => {
                const isOpen = expandedZona === zona.id;
                const ubics  = zonaUbics[zona.id] ?? [];
                return (
                  <div key={zona.id}>
                    {/* Fila de zona */}
                    <div className={`flex items-center gap-3 px-5 py-3.5 transition-colors ${isOpen ? "bg-blue-50/60" : "hover:bg-slate-50"}`}>
                      {/* Chevron + nombre */}
                      <button type="button" onClick={() => toggleZona(zona.id)}
                        className="flex flex-1 items-center gap-2.5 text-left">
                        <svg className={`h-4 w-4 flex-shrink-0 text-slate-400 transition-transform ${isOpen ? "rotate-90" : ""}`}
                          fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                          <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                        <div>
                          <p className="text-sm font-semibold" style={{ color: INK }}>{zona.nombre}</p>
                          {zona.descripcion && (
                            <p className="text-xs text-slate-400 truncate max-w-xs">{zona.descripcion}</p>
                          )}
                        </div>
                      </button>
                      {/* Badge contador de ubicaciones */}
                      {zonaUbics[zona.id] !== undefined && (
                        <span className="flex-shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-500">
                          {zonaUbics[zona.id].length} ubic.
                        </span>
                      )}
                      <button onClick={() => eliminar(zona.id)} disabled={deleting === zona.id}
                        className="flex-shrink-0 rounded-lg border border-red-100 px-2.5 py-1 text-xs font-medium text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40">
                        {deleting === zona.id ? "…" : "Eliminar"}
                      </button>
                    </div>

                    {/* Bloque expandible de ubicaciones */}
                    {isOpen && (
                      <div className="border-t border-blue-100 bg-blue-50/30 px-5 pb-4 pt-3">
                        <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-blue-400">
                          Ubicaciones de {zona.nombre}
                        </p>

                        {loadingUbic === zona.id ? (
                          <div className="space-y-1.5 pb-2">
                            {[1,2].map(i => <div key={i} className="h-8 animate-pulse rounded bg-blue-100/70" />)}
                          </div>
                        ) : ubics.length === 0 ? (
                          <p className="mb-3 text-xs text-slate-400">Sin ubicaciones — agrega la primera abajo.</p>
                        ) : (
                          <div className="mb-3 divide-y divide-blue-100 overflow-hidden rounded-xl border border-blue-100 bg-white">
                            {ubics.map(u => (
                              <div key={u.id} className="flex items-center justify-between px-3 py-2.5 hover:bg-slate-50">
                                <div>
                                  <p className="text-sm font-medium" style={{ color: INK }}>{u.nombre}</p>
                                  {u.descripcion && <p className="text-xs text-slate-400">{u.descripcion}</p>}
                                </div>
                                <button
                                  onClick={() => eliminarUbicacion(u.id, zona.id)}
                                  disabled={deletingUbic === u.id}
                                  className="ml-3 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-slate-300 hover:bg-red-50 hover:text-red-400 disabled:opacity-40">
                                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                                    <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round"/>
                                  </svg>
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Mini-form añadir ubicación */}
                        <form onSubmit={e => crearUbicacion(e, zona.id)} className="flex items-center gap-2">
                          <input
                            value={newUbicName[zona.id] ?? ""}
                            onChange={e => setNewUbicName(p => ({ ...p, [zona.id]: e.target.value }))}
                            placeholder="Nueva ubicación…"
                            required
                            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                          <input
                            value={newUbicDesc[zona.id] ?? ""}
                            onChange={e => setNewUbicDesc(p => ({ ...p, [zona.id]: e.target.value }))}
                            placeholder="Descripción (opcional)"
                            className="w-40 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                          <button type="submit" disabled={savingUbic === zona.id}
                            className="flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                            style={{ backgroundColor: SIGNAL }}>
                            {savingUbic === zona.id ? "…" : "+ Añadir"}
                          </button>
                        </form>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            /* ── Accesos / Áreas: tabla simple ──────────────── */
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-50 bg-slate-50/80 text-left">
                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Nombre</th>
                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Descripción</th>
                  {tab === "areas" && (
                    <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Activo</th>
                  )}
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {items.map(item => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3 font-semibold" style={{ color: INK }}>{item.nombre}</td>
                    <td className="max-w-xs truncate px-5 py-3 text-slate-500">{item.descripcion ?? "—"}</td>
                    {tab === "areas" && (
                      <td className="px-5 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          item.activo ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
                        }`}>
                          {item.activo ? "Activo" : "Inactivo"}
                        </span>
                      </td>
                    )}
                    <td className="px-5 py-3 text-right">
                      <button onClick={() => eliminar(item.id)} disabled={deleting === item.id}
                        className="rounded-lg border border-red-100 px-2.5 py-1 text-xs font-medium text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40">
                        {deleting === item.id ? "…" : "Eliminar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* ── Formulario añadir ─────────────────────────────── */}
        <div className="border-t border-slate-100 bg-slate-50 px-5 py-4">
          {error && <p className="mb-2 text-xs font-medium text-red-600">{error}</p>}
          <div className="mb-2 flex items-center gap-1.5">
            <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
              Agregar {tab === "zonas" ? "zona" : tab === "accesos" ? "punto de acceso" : "área"}
            </p>
            <Ayuda>
              {tab === "zonas"
                ? "Zona: subdivisión del recinto (Cancha, VIP, Palcos…) que se asigna a los invitados y define el color/etiqueta del gafete. Cada zona agrupa ubicaciones."
                : tab === "accesos"
                ? "Punto de acceso: entrada física (portón, torniquete) por la que ingresa el invitado; se imprime en el gafete como referencia para el guardia."
                : "Área autorizada: espacio específico del recinto donde el invitado puede circular, además de su zona asignada."}
            </Ayuda>
          </div>
          <form onSubmit={crear} className="flex items-center gap-2">
            <input required value={nombre} onChange={e => setNombre(e.target.value)}
              placeholder={meta.placeholder}
              className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
            <input value={desc} onChange={e => setDesc(e.target.value)}
              placeholder="Descripción (opcional)"
              className="w-44 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
            <button type="submit" disabled={saving}
              className="flex-shrink-0 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              style={{ backgroundColor: SIGNAL }}>
              {saving ? "…" : "+ Añadir"}
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}
