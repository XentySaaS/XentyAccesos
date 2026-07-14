/**
 * Verificación de documentos — workspace drill-down de 3 columnas.
 * Proveedores (con conteos) → Empleados del proveedor → Documentos del empleado (preview + acciones).
 * La agregación y los conteos vienen del backend (paginado) para escalar a mucho volumen.
 * Filtros: estado (pendientes/aprobados/rechazados), evento, "solo mis eventos", y búsqueda por
 * nombre en cada columna.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import api from "../api/client";

interface Prov { proveedor_id: number; proveedor_nombre: string; docs: number; empleados: number; }
interface Emp { emp_id: number; emp_nombre: string; docs: number; }
interface EventoLite { id: number; nombre: string; }
interface Documento {
  id: number;
  empleado: number;
  empleado_nombre: string;
  tipo_documento: number;
  tipo_documento_nombre: string;
  proveedor_nombre: string;
  archivo: string | null;
  tipo_archivo: string | null;
  estado: number;
  motivo_rechazo: string | null;
  creado: string;
}

const INK = "#0F1B2D";
type Estado = 0 | 1 | 2;
const TAB_LABEL: Record<Estado, string> = { 0: "Pendientes", 1: "Aprobados", 2: "Rechazados" };
const BADGE_STYLE: Record<number, { bg: string; text: string }> = {
  0: { bg: "bg-amber-100", text: "text-amber-800" },
  1: { bg: "bg-green-100", text: "text-green-800" },
  2: { bg: "bg-red-100", text: "text-red-700" },
};

function fmtFecha(iso: string) {
  return new Date(iso).toLocaleString("es-MX", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

const searchCls = "h-9 w-full rounded-lg border border-slate-200 bg-white pl-8 pr-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100";

function Lupa() {
  return (
    <svg className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
    </svg>
  );
}

export default function Verificacion() {
  // Filtros globales
  const [estado, setEstado] = useState<Estado>(0);
  const [evento, setEvento] = useState<string>("");
  const [misEventos, setMisEventos] = useState(false);
  const [eventos, setEventos] = useState<EventoLite[]>([]);
  const [orden, setOrden] = useState("pendientes");

  // Columnas (con paginación "cargar más": el backend pagina a 25/página)
  const [provs, setProvs] = useState<Prov[]>([]);
  const [provQ, setProvQ] = useState("");
  const [provSel, setProvSel] = useState<Prov | null>(null);
  const [loadingProv, setLoadingProv] = useState(false);
  const [provPage, setProvPage] = useState(1);
  const [provMore, setProvMore] = useState(false);
  const [moreProv, setMoreProv] = useState(false);

  const [emps, setEmps] = useState<Emp[]>([]);
  const [empQ, setEmpQ] = useState("");
  const [empSel, setEmpSel] = useState<Emp | null>(null);
  const [loadingEmp, setLoadingEmp] = useState(false);
  const [empPage, setEmpPage] = useState(1);
  const [empMore, setEmpMore] = useState(false);
  const [moreEmp, setMoreEmp] = useState(false);

  const [docs, setDocs] = useState<Documento[]>([]);
  const [docSel, setDocSel] = useState<Documento | null>(null);
  const [loadingDocs, setLoadingDocs] = useState(false);

  // Preview + acciones
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loadingBlob, setLoadingBlob] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [motivoModal, setMotivoModal] = useState(false);
  const [motivo, setMotivo] = useState("");
  const motivoRef = useRef<HTMLTextAreaElement>(null);

  // ── Cargadores ────────────────────────────────────────────────
  const loadProvs = useCallback((page = 1) => {
    const p = new URLSearchParams({ estado: String(estado), orden, page: String(page) });
    if (evento) p.set("evento", evento);
    if (misEventos) p.set("mis_eventos", "1");
    if (provQ.trim()) p.set("search", provQ.trim());
    page === 1 ? setLoadingProv(true) : setMoreProv(true);
    api.get(`/api/verificacion/proveedores/?${p}`)
      .then(r => {
        const res: Prov[] = r.data.results ?? [];
        setProvs(prev => (page === 1 ? res : [...prev, ...res]));
        setProvMore(!!r.data.next);
        setProvPage(page);
      })
      .catch(() => { if (page === 1) setProvs([]); })
      .finally(() => { setLoadingProv(false); setMoreProv(false); });
  }, [estado, evento, misEventos, provQ, orden]);

  const loadEmps = useCallback((page = 1) => {
    if (!provSel) { setEmps([]); return; }
    const p = new URLSearchParams({ estado: String(estado), proveedor: String(provSel.proveedor_id), orden, page: String(page) });
    if (evento) p.set("evento", evento);
    if (misEventos) p.set("mis_eventos", "1");
    if (empQ.trim()) p.set("search", empQ.trim());
    page === 1 ? setLoadingEmp(true) : setMoreEmp(true);
    api.get(`/api/verificacion/empleados/?${p}`)
      .then(r => {
        const res: Emp[] = r.data.results ?? [];
        setEmps(prev => (page === 1 ? res : [...prev, ...res]));
        setEmpMore(!!r.data.next);
        setEmpPage(page);
      })
      .catch(() => { if (page === 1) setEmps([]); })
      .finally(() => { setLoadingEmp(false); setMoreEmp(false); });
  }, [provSel, estado, evento, misEventos, empQ, orden]);

  const loadDocs = useCallback(() => {
    if (!empSel) { setDocs([]); return; }
    setLoadingDocs(true);
    api.get(`/api/documentos-empleado/?empleado=${empSel.emp_id}&estado=${estado}`)
      .then(r => setDocs(r.data.results ?? r.data))
      .catch(() => setDocs([]))
      .finally(() => setLoadingDocs(false));
  }, [empSel, estado]);

  // Lista de eventos para el filtro (cambia con "mis eventos").
  useEffect(() => {
    const p = new URLSearchParams();
    if (misEventos) p.set("mis_eventos", "1");
    api.get(`/api/verificacion/eventos/?${p}`).then(r => setEventos(r.data.eventos ?? [])).catch(() => setEventos([]));
  }, [misEventos]);

  // Al cambiar filtros globales, reinicia las selecciones.
  useEffect(() => { setProvSel(null); setEmps([]); setEmpSel(null); setDocs([]); setDocSel(null); }, [estado, evento, misEventos]);

  // Proveedores: recarga inmediata en filtros; debounce en búsqueda.
  useEffect(() => { const t = setTimeout(() => loadProvs(1), provQ ? 300 : 0); return () => clearTimeout(t); }, [loadProvs, provQ]);
  // Empleados: al elegir proveedor / cambiar filtros; debounce en búsqueda.
  useEffect(() => { const t = setTimeout(() => loadEmps(1), empQ ? 300 : 0); return () => clearTimeout(t); }, [loadEmps, empQ]);
  // Documentos del empleado seleccionado.
  useEffect(() => { loadDocs(); }, [loadDocs]);

  // Reinicios en cascada.
  useEffect(() => { setEmpSel(null); setEmpQ(""); setDocs([]); setDocSel(null); }, [provSel?.proveedor_id]);
  useEffect(() => { setDocSel(null); }, [empSel?.emp_id, estado]);
  // Auto-selecciona el primer documento de la bandeja.
  useEffect(() => { setDocSel(prev => (prev && docs.some(d => d.id === prev.id) ? prev : docs[0] ?? null)); }, [docs]);

  // Preview autenticado (blob) del documento seleccionado.
  useEffect(() => {
    if (blobUrl) { URL.revokeObjectURL(blobUrl); setBlobUrl(null); }
    if (!docSel?.archivo) return;
    setLoadingBlob(true);
    api.get(`/api/documentos-empleado/${docSel.id}/download/`, { responseType: "blob" })
      .then(r => setBlobUrl(URL.createObjectURL(r.data)))
      .catch(() => setBlobUrl(null))
      .finally(() => setLoadingBlob(false));
  }, [docSel?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }, [blobUrl]);

  // ── Acciones ──────────────────────────────────────────────────
  function refrescarConteos() { loadDocs(); loadEmps(); loadProvs(); }

  async function aprobar(doc: Documento) {
    setProcesando(true);
    try {
      await api.post(`/api/documentos-empleado/${doc.id}/aprobar/`);
      refrescarConteos();
    } finally { setProcesando(false); }
  }

  async function rechazar(doc: Documento) {
    if (!motivo.trim()) return;
    setProcesando(true);
    try {
      await api.post(`/api/documentos-empleado/${doc.id}/rechazar/`, { motivo });
      setMotivoModal(false); setMotivo("");
      refrescarConteos();
    } finally { setProcesando(false); }
  }

  function abrirRechazo() { setMotivoModal(true); setMotivo(""); setTimeout(() => motivoRef.current?.focus(), 60); }

  const esPDF = docSel?.tipo_archivo === "pdf" || docSel?.archivo?.toLowerCase().endsWith(".pdf");
  const nombreArchivo = docSel?.archivo?.split("/").pop() ?? "sin-archivo";

  return (
    <div className="flex h-full flex-col">
      {/* Header + filtros */}
      <div className="mb-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ backgroundColor: "#EFF6FF" }}>
            <svg className="h-5 w-5" style={{ color: "#2563EB" }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
            </svg>
          </div>
          <div>
            <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Verificación de documentos</h1>
            <p className="text-xs text-slate-500">Revisa por proveedor → empleado → documento</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Tabs de estado */}
          <div className="inline-flex overflow-hidden rounded-lg border border-slate-200">
            {([0, 1, 2] as Estado[]).map(t => (
              <button key={t} onClick={() => setEstado(t)}
                className={`px-3 py-1.5 text-xs font-semibold transition-colors ${estado === t ? "text-white" : "bg-white text-slate-500 hover:bg-slate-50"}`}
                style={estado === t ? { backgroundColor: "#2563EB" } : {}}>
                {TAB_LABEL[t]}
              </button>
            ))}
          </div>
          {/* Filtro por evento */}
          <select value={evento} onChange={e => setEvento(e.target.value)}
            className="h-8 rounded-lg border border-slate-200 bg-white px-2 text-xs text-slate-600 outline-none focus:border-blue-400">
            <option value="">Todos los eventos</option>
            {eventos.map(ev => <option key={ev.id} value={ev.id}>{ev.nombre}</option>)}
          </select>
          {/* Solo mis eventos */}
          <label className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600">
            <input type="checkbox" checked={misEventos} onChange={e => { setMisEventos(e.target.checked); setEvento(""); }} className="accent-blue-600" />
            Solo mis eventos
          </label>
          {/* Orden */}
          <select value={orden} onChange={e => setOrden(e.target.value)} title="Ordenar proveedores y empleados"
            className="ml-auto h-8 rounded-lg border border-slate-200 bg-white px-2 text-xs text-slate-600 outline-none focus:border-blue-400">
            <option value="pendientes">Ordenar: más pendientes</option>
            <option value="recientes">Más recientes</option>
            <option value="antiguos">Más antiguos</option>
            <option value="az">A – Z</option>
            <option value="za">Z – A</option>
          </select>
        </div>
      </div>

      {/* Columnas */}
      <div className="flex min-h-0 flex-1 gap-3 overflow-hidden">

        {/* ① Proveedores */}
        <div className="flex w-64 flex-shrink-0 flex-col overflow-hidden rounded-card bg-white shadow-card">
          <div className="border-b border-slate-100 p-2.5">
            <p className="mb-2 px-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">Proveedores</p>
            <div className="relative"><Lupa /><input value={provQ} onChange={e => setProvQ(e.target.value)} placeholder="Buscar proveedor…" className={searchCls} /></div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingProv ? <Skeleton /> : provs.length === 0 ? (
              <Vacio texto={`Sin proveedores con ${TAB_LABEL[estado].toLowerCase()}.`} />
            ) : provs.map(p => {
              const activo = provSel?.proveedor_id === p.proveedor_id;
              return (
                <button key={p.proveedor_id} onClick={() => setProvSel(p)}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50"
                  style={{ backgroundColor: activo ? "#EFF6FF" : "transparent", borderLeft: activo ? "3px solid #2563EB" : "3px solid transparent" }}>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold" style={{ color: INK }}>{p.proveedor_nombre || "—"}</p>
                    <p className="text-[11px] text-slate-400">{p.empleados} empleado{p.empleados !== 1 ? "s" : ""}</p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-bold ${BADGE_STYLE[estado].bg} ${BADGE_STYLE[estado].text}`}>{p.docs}</span>
                </button>
              );
            })}
            <CargarMas show={provMore} loading={moreProv} onClick={() => loadProvs(provPage + 1)} />
          </div>
        </div>

        {/* ② Empleados */}
        <div className="flex w-64 flex-shrink-0 flex-col overflow-hidden rounded-card bg-white shadow-card">
          <div className="border-b border-slate-100 p-2.5">
            <p className="mb-2 px-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">Empleados</p>
            <div className="relative"><Lupa /><input value={empQ} onChange={e => setEmpQ(e.target.value)} placeholder="Buscar empleado…" disabled={!provSel} className={`${searchCls} disabled:bg-slate-50`} /></div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {!provSel ? <Vacio texto="Elige un proveedor." /> : loadingEmp ? <Skeleton /> : emps.length === 0 ? (
              <Vacio texto="Sin empleados en esta bandeja." />
            ) : emps.map(e => {
              const activo = empSel?.emp_id === e.emp_id;
              return (
                <button key={e.emp_id} onClick={() => setEmpSel(e)}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50"
                  style={{ backgroundColor: activo ? "#EFF6FF" : "transparent", borderLeft: activo ? "3px solid #2563EB" : "3px solid transparent" }}>
                  <p className="min-w-0 flex-1 truncate text-sm font-medium text-slate-700">{e.emp_nombre || "—"}</p>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-bold ${BADGE_STYLE[estado].bg} ${BADGE_STYLE[estado].text}`}>{e.docs}</span>
                </button>
              );
            })}
            <CargarMas show={empMore} loading={moreEmp} onClick={() => loadEmps(empPage + 1)} />
          </div>
        </div>

        {/* ③ Documentos + preview */}
        <div className="flex flex-1 flex-col overflow-hidden rounded-card bg-white shadow-card">
          {!empSel ? (
            <Centro texto="Selecciona un empleado para revisar sus documentos." />
          ) : (
            <>
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-sm font-bold" style={{ color: INK }}>{empSel.emp_nombre}</p>
                <p className="text-xs text-slate-500">{provSel?.proveedor_nombre}</p>
              </div>

              {/* Selector de documentos del empleado */}
              {loadingDocs ? (
                <div className="p-3"><Skeleton /></div>
              ) : docs.length === 0 ? (
                <Centro texto={`Sin documentos ${TAB_LABEL[estado].toLowerCase()} para este empleado.`} />
              ) : (
                <>
                  <div className="flex flex-wrap gap-1.5 border-b border-slate-100 px-4 py-2.5">
                    {docs.map(d => {
                      const activo = docSel?.id === d.id;
                      return (
                        <button key={d.id} onClick={() => setDocSel(d)} title={fmtFecha(d.creado)}
                          className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition ${activo ? "border-blue-400 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
                          {d.tipo_documento_nombre || `#${d.tipo_documento}`}
                        </button>
                      );
                    })}
                  </div>

                  {/* Preview */}
                  <div className="flex flex-1 items-center justify-center overflow-hidden bg-slate-50 p-3">
                    {!docSel?.archivo ? (
                      <Centro texto="Sin archivo adjunto" />
                    ) : loadingBlob ? (
                      <div className="flex flex-col items-center gap-2"><div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" /><p className="text-sm text-slate-400">Cargando archivo…</p></div>
                    ) : !blobUrl ? (
                      <Centro texto="No se pudo cargar el archivo." />
                    ) : esPDF ? (
                      <iframe src={blobUrl} className="h-full w-full rounded-lg" title="Documento PDF" />
                    ) : (
                      <img src={blobUrl} alt="Documento" className="max-h-full max-w-full rounded-lg object-contain shadow-sm" />
                    )}
                  </div>

                  {/* Acciones */}
                  {docSel && (
                    <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-4 py-3">
                      <div className="min-w-0">
                        <p className="font-mono text-[11px] text-slate-400">{nombreArchivo}{docSel.tipo_archivo && <span className="ml-2 uppercase">{docSel.tipo_archivo}</span>}</p>
                        {docSel.motivo_rechazo && <p className="mt-0.5 truncate text-xs text-red-600">Motivo: {docSel.motivo_rechazo}</p>}
                      </div>
                      <div className="flex shrink-0 gap-2">
                        {blobUrl && <a href={blobUrl} download={nombreArchivo} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">Descargar ↓</a>}
                        {(docSel.estado === 0 || docSel.estado === 2) && (
                          <button onClick={abrirRechazo} disabled={procesando} className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition disabled:opacity-50" style={{ borderColor: "#DC2626", color: "#DC2626" }}>Rechazar</button>
                        )}
                        {(docSel.estado === 0 || docSel.estado === 2) && (
                          <button onClick={() => aprobar(docSel)} disabled={procesando} className="rounded-lg px-4 py-1.5 text-xs font-semibold text-white transition disabled:opacity-50" style={{ backgroundColor: "#16A34A" }}>{procesando ? "Guardando…" : "Aprobar"}</button>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Modal motivo de rechazo */}
      {motivoModal && docSel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Rechazar documento</h2>
            <p className="mb-4 text-sm text-slate-500">Explica el motivo — el proveedor lo verá.</p>
            <textarea ref={motivoRef} required rows={3} value={motivo} onChange={e => setMotivo(e.target.value)}
              placeholder="Documento ilegible, información incorrecta…"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-400 focus:ring-1 focus:ring-red-100" />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => { setMotivoModal(false); setMotivo(""); }} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button onClick={() => rechazar(docSel)} disabled={procesando || !motivo.trim()} className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: "#DC2626" }}>Rechazar documento</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Skeleton() {
  return <div className="space-y-2 p-3">{[1, 2, 3].map(i => <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-100" />)}</div>;
}
function CargarMas({ show, loading, onClick }: { show: boolean; loading: boolean; onClick: () => void }) {
  if (!show) return null;
  return (
    <button onClick={onClick} disabled={loading}
      className="w-full border-t border-slate-100 py-2.5 text-center text-xs font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-50">
      {loading ? "Cargando…" : "Cargar más"}
    </button>
  );
}
function Vacio({ texto }: { texto: string }) {
  return <div className="flex flex-col items-center justify-center py-12 px-4 text-center"><p className="text-xs font-medium text-slate-400">{texto}</p></div>;
}
function Centro({ texto }: { texto: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
        <svg className="h-7 w-7 text-slate-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
      </div>
      <p className="text-sm font-medium text-slate-400">{texto}</p>
    </div>
  );
}
