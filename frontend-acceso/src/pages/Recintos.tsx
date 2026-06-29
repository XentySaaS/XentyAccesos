import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

/* ── tipos ─────────────────────────────────────────────────── */
interface Recinto {
  id: number;
  nombre: string | null;
  codigo: string | null;
  telefono: string | null;
  descripcion: string | null;
}

interface SubItem { id: number; nombre: string; descripcion: string | null; activo?: boolean; }

type SubTab = "zonas" | "accesos" | "areas";

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const TAB_META: Record<SubTab, { label: string; endpoint: string; placeholder: string }> = {
  zonas:   { label: "Zonas",             endpoint: "/api/zonas/",            placeholder: "Ej. Zona Norte, Patio Central…" },
  accesos: { label: "Puntos de acceso",  endpoint: "/api/accesos/",          placeholder: "Ej. Entrada principal, Portón 3…" },
  areas:   { label: "Áreas autorizadas", endpoint: "/api/areas-autorizadas/",placeholder: "Ej. Almacén, Sala de reuniones…" },
};

/* ── componente principal ──────────────────────────────────── */
export default function Recintos() {
  const [items,   setItems]   = useState<Recinto[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState<"crear" | "editar" | null>(null);
  const [gestion, setGestion] = useState<Recinto | null>(null);
  const [sel,     setSel]     = useState<Recinto | null>(null);
  const [error,   setError]   = useState<string | null>(null);
  const [saving,  setSaving]  = useState(false);

  // form recinto
  const [nombre,    setNombre]    = useState("");
  const [codigo,    setCodigo]    = useState("");
  const [telefono,  setTelefono]  = useState("");
  const [descripcion,setDescripcion]=useState("");

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
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "No se pudo guardar.");
    } finally { setSaving(false); }
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ backgroundColor: "#EFF6FF" }}>
          <svg className="h-5 w-5" style={{ color: SIGNAL }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
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

      {/* Tabla */}
      <div className="overflow-hidden rounded-card bg-white shadow-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left">
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
                  <div className="flex gap-1.5">
                    <button onClick={() => abrirEditar(r)}
                      className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">
                      Editar
                    </button>
                    <button onClick={() => setGestion(r)}
                      className="rounded-lg px-3 py-1 text-xs font-semibold text-white transition hover:opacity-90"
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

      {/* Modal crear / editar recinto */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={guardar} className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>
              {modal === "crear" ? "Nuevo recinto" : "Editar recinto"}
            </h2>
            <p className="mb-4 text-xs text-slate-400">Los campos marcados * son obligatorios.</p>
            {error && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}
            <div className="space-y-3">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold text-slate-600">Nombre *</span>
                <input required value={nombre} onChange={e => setNombre(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold text-slate-600">Código</span>
                  <input value={codigo} onChange={e => setCodigo(e.target.value)}
                    placeholder="REC-01"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold text-slate-600">Teléfono</span>
                  <input value={telefono} onChange={e => setTelefono(e.target.value)}
                    placeholder="+52 55…"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                </label>
              </div>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold text-slate-600">Descripción</span>
                <textarea rows={2} value={descripcion} onChange={e => setDescripcion(e.target.value)}
                  className="w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </label>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: SIGNAL }}>
                {saving ? "Guardando…" : modal === "crear" ? "Crear recinto" : "Guardar cambios"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal gestionar sub-entidades */}
      {gestion && (
        <GestionModal recinto={gestion} onClose={() => setGestion(null)} />
      )}
    </div>
  );
}

/* ── Modal de gestión de sub-entidades ─────────────────────── */
function GestionModal({ recinto, onClose }: { recinto: Recinto; onClose: () => void }) {
  const [tab,    setTab]    = useState<SubTab>("zonas");
  const [items,  setItems]  = useState<SubItem[]>([]);
  const [loading,setLoading]= useState(true);
  const [nombre, setNombre] = useState("");
  const [desc,   setDesc]   = useState("");
  const [saving, setSaving] = useState(false);
  const [error,  setError]  = useState("");
  const [deleting,setDeleting]=useState<number | null>(null);

  const meta = TAB_META[tab];

  async function cargarSub() {
    setLoading(true); setItems([]);
    try {
      const { data } = await api.get(meta.endpoint, { params: { recinto: recinto.id } });
      setItems(Array.isArray(data) ? data : data.results ?? []);
    } finally { setLoading(false); }
  }

  useEffect(() => { setNombre(""); setDesc(""); setError(""); cargarSub(); }, [tab]);

  async function crear(e: FormEvent) {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await api.post(meta.endpoint, { nombre, descripcion: desc || null, recinto: recinto.id });
      setNombre(""); setDesc(""); await cargarSub();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.response?.data?.nombre?.[0] ?? "No se pudo crear.");
    } finally { setSaving(false); }
  }

  async function eliminar(id: number) {
    if (!confirm("¿Eliminar este elemento?")) return;
    setDeleting(id);
    try {
      await api.delete(`${meta.endpoint}${id}/`);
      await cargarSub();
    } finally { setDeleting(null); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="flex w-full max-w-2xl flex-col overflow-hidden rounded-modal bg-white shadow-panel"
        style={{ maxHeight: "80vh" }}>

        {/* Cabecera */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-base font-bold" style={{ color: "#0F1B2D" }}>
              Gestionar — {recinto.nombre}
            </h2>
            <p className="text-xs text-slate-400">Zonas, puntos de acceso y áreas autorizadas</p>
          </div>
          <button onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-100 px-6">
          {(Object.keys(TAB_META) as SubTab[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`mr-1 py-3 text-xs font-semibold transition-colors ${
                tab === t ? "border-b-2 text-blue-600" : "text-slate-400 hover:text-slate-600"
              }`}
              style={tab === t ? { borderBottomColor: "#2563EB", color: "#2563EB" } : {}}>
              {TAB_META[t].label}
            </button>
          ))}
        </div>

        {/* Lista */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="space-y-2 p-4">
              {[1,2,3].map(i => <div key={i} className="h-10 animate-pulse rounded bg-slate-100" />)}
            </div>
          ) : items.length === 0 ? (
            <div className="py-10 text-center text-sm text-slate-400">
              Sin {TAB_META[tab].label.toLowerCase()} — agrega el primero abajo.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-50 text-left">
                  <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Nombre</th>
                  <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Descripción</th>
                  {tab === "areas" && (
                    <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Activo</th>
                  )}
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {items.map(item => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 font-semibold" style={{ color: "#0F1B2D" }}>{item.nombre}</td>
                    <td className="max-w-xs truncate px-4 py-2.5 text-slate-500">{item.descripcion ?? "—"}</td>
                    {tab === "areas" && (
                      <td className="px-4 py-2.5">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${item.activo ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-500"}`}>
                          {item.activo ? "Activo" : "Inactivo"}
                        </span>
                      </td>
                    )}
                    <td className="px-4 py-2.5">
                      <button
                        onClick={() => eliminar(item.id)}
                        disabled={deleting === item.id}
                        className="rounded-lg border border-red-100 px-2 py-1 text-xs font-medium text-red-500 transition hover:bg-red-50 disabled:opacity-40">
                        {deleting === item.id ? "…" : "Eliminar"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Formulario añadir */}
        <div className="border-t border-slate-100 bg-slate-50 px-6 py-4">
          {error && (
            <p className="mb-2 text-xs text-red-600">{error}</p>
          )}
          <form onSubmit={crear} className="flex items-end gap-2">
            <div className="flex-1">
              <label className="mb-1 block text-xs font-semibold text-slate-500">
                Nombre *
              </label>
              <input required value={nombre} onChange={e => setNombre(e.target.value)}
                placeholder={meta.placeholder}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs font-semibold text-slate-500">Descripción</label>
              <input value={desc} onChange={e => setDesc(e.target.value)}
                placeholder="Opcional…"
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
            </div>
            <button type="submit" disabled={saving}
              className="flex-shrink-0 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
              style={{ backgroundColor: SIGNAL }}>
              {saving ? "…" : "+ Añadir"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
