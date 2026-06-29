/**
 * Verificación de documentos — diseño split panel.
 * Lista de bandeja (izq) + panel de previsualización y acciones (der).
 */
import { useEffect, useRef, useState } from "react";
import api from "../api/client";

interface Documento {
  id: number;
  empleado: number;
  empleado_nombre: string;
  tipo_documento: number;
  tipo_documento_nombre: string;
  proveedor_nombre: string;
  archivo: string | null;
  tipo_archivo: string | null;
  estado: number; // 0=pendiente 1=verificado 2=rechazado
  motivo_rechazo: string | null;
  creado: string;
}

type Tab = 0 | 1 | 2;

const TAB_LABEL: Record<Tab, string> = { 0: "Pendientes", 1: "Aprobados", 2: "Rechazados" };
const BADGE_STYLE: Record<number, { bg: string; text: string }> = {
  0: { bg: "bg-amber-100",  text: "text-amber-800"  },
  1: { bg: "bg-green-100",  text: "text-green-800"  },
  2: { bg: "bg-red-100",    text: "text-red-700"    },
};

function fmtFecha(iso: string) {
  return new Date(iso).toLocaleString("es-MX", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export default function Verificacion() {
  const [docs,     setDocs]     = useState<Documento[]>([]);
  const [tab,      setTab]      = useState<Tab>(0);
  const [sel,      setSel]      = useState<Documento | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [procesando,setProcesando] = useState(false);
  const [motivoModal, setMotivoModal] = useState(false);
  const [motivo,   setMotivo]   = useState("");
  const motivoRef = useRef<HTMLTextAreaElement>(null);

  async function cargar(estado: Tab) {
    setLoading(true);
    try {
      const d = await api.get("/api/documentos-empleado/", { params: { estado } });
      setDocs(d.data.results ?? d.data);
    } finally { setLoading(false); }
  }

  useEffect(() => { cargar(tab); setSel(null); }, [tab]);

  const nombre = (d: Documento) => d.empleado_nombre || `#${d.empleado}`;
  const tipo   = (d: Documento) => d.tipo_documento_nombre || `#${d.tipo_documento}`;
  const pendientes = tab === 0 ? docs.length : docs.filter(d => d.estado === 0).length;

  async function aprobar(doc: Documento) {
    setProcesando(true);
    try {
      await api.post(`/api/documentos-empleado/${doc.id}/aprobar/`);
      await cargar(tab);
      setSel(null);
    } finally { setProcesando(false); }
  }

  async function rechazar(doc: Documento) {
    if (!motivo.trim()) return;
    setProcesando(true);
    try {
      await api.post(`/api/documentos-empleado/${doc.id}/rechazar/`, { motivo });
      setMotivoModal(false); setMotivo("");
      await cargar(tab);
      setSel(null);
    } finally { setProcesando(false); }
  }

  function abrirRechazo() {
    setMotivoModal(true);
    setMotivo("");
    setTimeout(() => motivoRef.current?.focus(), 60);
  }

  const esPDF = sel?.archivo?.toLowerCase().endsWith(".pdf");

  return (
    <div className="flex h-full flex-col">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="mb-5 flex items-center gap-3">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{ backgroundColor: "#EFF6FF" }}>
          <svg className="h-5 w-5" style={{ color: "#2563EB" }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
          </svg>
        </div>
        <div>
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: "#0F1B2D" }}>
            Verificación de documentos
            {pendientes > 0 && (
              <span className="ml-2 rounded-full bg-amber-500 px-2 py-0.5 text-sm font-bold text-white align-middle">
                {pendientes}
              </span>
            )}
          </h1>
          <p className="text-xs text-slate-500">Bandeja de revisión documental</p>
        </div>
      </div>

      {/* ── Split layout ─────────────────────────────────────── */}
      <div className="flex flex-1 gap-4 overflow-hidden min-h-0">

        {/* ── Lista izquierda ─────────────────────────── */}
        <div
          className="flex w-96 flex-shrink-0 flex-col overflow-hidden rounded-card bg-white shadow-card"
        >
          {/* Tabs */}
          <div className="flex border-b border-slate-100">
            {([0, 1, 2] as Tab[]).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`flex-1 py-3 text-xs font-semibold transition-colors ${
                  tab === t
                    ? "border-b-2 text-blue-600"
                    : "text-slate-400 hover:text-slate-600"
                }`}
                style={tab === t ? { borderBottomColor: "#2563EB", color: "#2563EB" } : {}}>
                {TAB_LABEL[t]}
              </button>
            ))}
          </div>

          {/* Items */}
          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="space-y-2 p-3">
                {[1,2,3].map(i => (
                  <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />
                ))}
              </div>
            )}
            {!loading && docs.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-sm font-medium text-slate-400">Sin documentos en esta bandeja.</p>
              </div>
            )}
            {!loading && docs.map(doc => {
              const activo = sel?.id === doc.id;
              return (
                <button key={doc.id} onClick={() => setSel(doc)}
                  className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors"
                  style={{
                    backgroundColor: activo ? "#EFF6FF" : "transparent",
                    borderLeft: activo ? "3px solid #2563EB" : "3px solid transparent",
                  }}>
                  {/* Icono tipo */}
                  <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-slate-100">
                    <svg className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold" style={{ color: "#0F1B2D" }}>
                      {nombre(doc)}
                    </p>
                    <p className="truncate text-xs text-slate-500">{tipo(doc)} · {doc.proveedor_nombre}</p>
                    <p className="tabular mt-0.5 font-mono text-[10px] text-slate-400">
                      {fmtFecha(doc.creado)}
                    </p>
                  </div>
                  <span className={`mt-0.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${BADGE_STYLE[doc.estado]?.bg} ${BADGE_STYLE[doc.estado]?.text}`}>
                    {TAB_LABEL[doc.estado as Tab] ?? doc.estado}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Panel derecho ───────────────────────────── */}
        <div className="flex flex-1 flex-col overflow-hidden rounded-card bg-white shadow-card">
          {!sel ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
                <svg className="h-8 w-8 text-slate-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
                </svg>
              </div>
              <p className="text-sm font-medium text-slate-400">Selecciona un documento de la lista.</p>
            </div>
          ) : (
            <>
              {/* Cabecera del documento */}
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                <div>
                  <p className="text-base font-bold" style={{ color: "#0F1B2D" }}>
                    {tipo(sel)}
                  </p>
                  <p className="text-sm text-slate-500">{nombre(sel)} · {sel.proveedor_nombre}</p>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${BADGE_STYLE[sel.estado]?.bg} ${BADGE_STYLE[sel.estado]?.text}`}>
                  {TAB_LABEL[sel.estado as Tab]}
                </span>
              </div>

              {/* Previsualización */}
              <div className="flex flex-1 items-center justify-center overflow-hidden bg-slate-50 p-4">
                {!sel.archivo ? (
                  <div className="flex flex-col items-center gap-2 text-center">
                    <svg className="h-12 w-12 text-slate-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    </svg>
                    <p className="text-sm text-slate-400">Sin archivo adjunto</p>
                  </div>
                ) : esPDF ? (
                  <iframe src={sel.archivo} className="h-full w-full rounded-lg" title="Documento PDF" />
                ) : (
                  <img
                    src={sel.archivo} alt="Documento"
                    className="max-h-full max-w-full rounded-lg object-contain shadow-sm"
                  />
                )}
              </div>

              {/* Barra de acciones */}
              <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-3">
                {/* Metadatos */}
                <div className="min-w-0">
                  <p className="font-mono text-[11px] text-slate-400">
                    {sel.archivo
                      ? sel.archivo.split("/").pop()
                      : "sin-archivo"}
                    {sel.tipo_archivo && (
                      <span className="ml-2 uppercase">{sel.tipo_archivo}</span>
                    )}
                  </p>
                  {sel.motivo_rechazo && (
                    <p className="mt-0.5 truncate text-xs text-red-600">
                      Motivo: {sel.motivo_rechazo}
                    </p>
                  )}
                </div>

                <div className="flex gap-2">
                  {sel.archivo && (
                    <a href={sel.archivo} target="_blank" rel="noreferrer"
                      className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">
                      Ver archivo ↗
                    </a>
                  )}
                  {(sel.estado === 0 || sel.estado === 2) && (
                    <button
                      onClick={abrirRechazo}
                      disabled={procesando}
                      className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition disabled:opacity-50"
                      style={{ borderColor: "#DC2626", color: "#DC2626" }}>
                      Rechazar
                    </button>
                  )}
                  {(sel.estado === 0 || sel.estado === 2) && (
                    <button
                      onClick={() => aprobar(sel)}
                      disabled={procesando}
                      className="rounded-lg px-4 py-1.5 text-xs font-semibold text-white transition disabled:opacity-50"
                      style={{ backgroundColor: "#16A34A" }}>
                      {procesando ? "Guardando…" : "Aprobar documento"}
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Modal motivo de rechazo ───────────────────────────── */}
      {motivoModal && sel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: "#0F1B2D" }}>Rechazar documento</h2>
            <p className="mb-4 text-sm text-slate-500">
              Explica el motivo — el proveedor lo verá.
            </p>
            <textarea
              ref={motivoRef}
              required rows={3} value={motivo}
              onChange={e => setMotivo(e.target.value)}
              placeholder="Documento ilegible, información incorrecta…"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-400 focus:ring-1 focus:ring-red-100"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button"
                onClick={() => { setMotivoModal(false); setMotivo(""); }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button
                onClick={() => rechazar(sel)}
                disabled={procesando || !motivo.trim()}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                style={{ backgroundColor: "#DC2626" }}>
                Rechazar documento
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
