import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

interface Sancion {
  id: number;
  empleado: number;
  empleado_nombre: string | null;
  evento: number | null;
  evento_nombre: string | null;
  cita: number | null;
  severidad: string | null;
  penalidad: string | null;
  motivo: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  creado: string;
}

interface EmpOpcion { id: number; nombre: string; empresa: string; }
interface EventoOpcion { id: number; nombre: string; estado: string; }

const INK = "#0F1B2D";
const QR_DIV_ID = "san-qr-reader";

const SEV_BADGE: Record<string, { bg: string; text: string }> = {
  bajo:  { bg: "bg-blue-100",   text: "text-blue-800"  },
  medio: { bg: "bg-amber-100",  text: "text-amber-800" },
  alto:  { bg: "bg-red-100",    text: "text-red-700"   },
};

const PEN_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  advertencia: { bg: "bg-amber-100",  text: "text-amber-800",  label: "Advertencia" },
  suspension:  { bg: "bg-orange-100", text: "text-orange-800", label: "Suspensión"  },
  baja:        { bg: "bg-red-100",    text: "text-red-700",    label: "Baja"        },
};

const FORM_INIT = {
  empleado: "", evento: "", severidad: "bajo", penalidad: "advertencia",
  motivo: "", fecha_inicio: "", fecha_fin: "",
};

export default function Sanciones() {
  const [sanciones, setSanciones] = useState<Sancion[]>([]);
  const [eventos,   setEventos]   = useState<EventoOpcion[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [form,      setForm]      = useState(FORM_INIT);
  const [saving,    setSaving]    = useState(false);
  const [error,     setError]     = useState("");
  // Severidad y penalidad solo las define el administrador (igual que el original WarningResource);
  // el guardia únicamente captura empleado, evento y motivo.
  const [esAdmin,   setEsAdmin]   = useState(false);

  // Búsqueda de empleado (autocomplete: un evento puede tener muchísimos asistentes).
  const [empLabel, setEmpLabel] = useState("");
  const [empQuery, setEmpQuery] = useState("");
  const [empSugs,  setEmpSugs]  = useState<EmpOpcion[]>([]);
  const [buscando, setBuscando] = useState(false);

  // Escaneo de QR del gafete (por si el empleado lo lleva).
  const [scanOpen,  setScanOpen]  = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const html5QrRef = useRef<Html5Qrcode | null>(null);
  const resolviendoRef = useRef(false);

  const cargar = () =>
    api.get("/api/sanciones/")
      .then(r => setSanciones(r.data.results ?? r.data))
      .finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);
  useEffect(() => {
    api.get("/api/auth/me/").then(r => setEsAdmin(r.data?.rol === "administrador")).catch(() => {});
    api.get("/api/sanciones/eventos/").then(r => setEventos(r.data ?? [])).catch(() => {});
  }, []);

  // Debounce de la búsqueda de empleado.
  useEffect(() => {
    if (empQuery.trim().length < 2) { setEmpSugs([]); return; }
    setBuscando(true);
    const t = setTimeout(() => {
      api.get<EmpOpcion[]>("/api/sanciones/buscar-empleados/", { params: { q: empQuery.trim() } })
        .then(r => setEmpSugs(r.data ?? []))
        .catch(() => setEmpSugs([]))
        .finally(() => setBuscando(false));
    }, 300);
    return () => clearTimeout(t);
  }, [empQuery]);

  function seleccionarEmpleado(e: EmpOpcion) {
    setForm(f => ({ ...f, empleado: String(e.id) }));
    setEmpLabel(e.empresa ? `${e.nombre} — ${e.empresa}` : e.nombre);
    setEmpQuery("");
    setEmpSugs([]);
  }

  function limpiarEmpleado() {
    setForm(f => ({ ...f, empleado: "" }));
    setEmpLabel("");
  }

  function abrirForm() {
    setError(""); setForm(FORM_INIT); setEmpLabel(""); setEmpQuery(""); setEmpSugs([]);
    setShowForm(true);
  }

  // ── Escaneo QR: resuelve el empleado (y su evento) del gafete ──────────────
  useEffect(() => {
    if (!scanOpen) return;
    const qr = new Html5Qrcode(QR_DIV_ID);
    html5QrRef.current = qr;
    let vivo = true;
    let iniciado = false;
    const detener = () => {
      try {
        qr.stop().catch(() => {}).finally(() => { try { qr.clear(); } catch { /* noop */ } });
      } catch { try { qr.clear(); } catch { /* noop */ } }
    };
    qr.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 220 },
      async (texto) => {
        if (!vivo || resolviendoRef.current) return;
        resolviendoRef.current = true;
        try {
          const { data } = await api.post("/api/sanciones/resolver-qr/", { qr: texto });
          setForm(f => ({ ...f, empleado: String(data.empleado_id), evento: data.evento_id ? String(data.evento_id) : f.evento }));
          setEmpLabel(data.empresa ? `${data.empleado_nombre} — ${data.empresa}` : data.empleado_nombre);
          setScanOpen(false);
        } catch (err: unknown) {
          const e = err as { response?: { data?: { detail?: string } } };
          setScanError(e?.response?.data?.detail ?? "QR no válido.");
        } finally {
          resolviendoRef.current = false;
        }
      },
      () => { /* frame sin QR: ignorar */ },
    ).then(() => { iniciado = true; if (!vivo) detener(); })
     .catch(() => { if (vivo) { setScanError("No se pudo acceder a la cámara. Revisa los permisos."); setScanOpen(false); } });

    return () => { vivo = false; html5QrRef.current = null; if (iniciado) detener(); };
  }, [scanOpen]);

  const crear = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.empleado) { setError("Selecciona o escanea un empleado."); return; }
    setSaving(true); setError("");
    try {
      const payload: Record<string, unknown> = {
        empleado: Number(form.empleado),
        evento: form.evento ? Number(form.evento) : null,
        motivo: form.motivo,
      };
      if (esAdmin) {
        payload.severidad = form.severidad;
        payload.penalidad = form.penalidad;
        payload.fecha_inicio = form.penalidad === "suspension" ? form.fecha_inicio : null;
        payload.fecha_fin    = form.penalidad === "suspension" ? form.fecha_fin    : null;
      }
      await api.post("/api/sanciones/", payload);
      setShowForm(false); setForm(FORM_INIT); setEmpLabel(""); cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(typeof e.response?.data === "string" ? e.response.data : JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  const F = form;
  const set = (k: keyof typeof FORM_INIT, v: string) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ backgroundColor: "#FEF2F2" }}>
          <svg className="h-5 w-5 text-red-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Sanciones</h1>
          <p className="text-xs text-slate-500">Registro de advertencias y suspensiones</p>
        </div>
        <button onClick={abrirForm}
          className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: "#DC2626" }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nueva sanción
        </button>
      </div>

      {/* Tabla */}
      <div className="overflow-hidden rounded-card bg-white shadow-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left">
              {["Empleado", "Evento", "Motivo", "Severidad", "Penalidad", "Período suspensión", "Fecha"].map(h => (
                <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading && (
              <tr><td colSpan={7} className="px-4 py-8">
                <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />)}</div>
              </td></tr>
            )}
            {!loading && sanciones.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-sm text-slate-400">
                Sin sanciones registradas.
              </td></tr>
            )}
            {!loading && sanciones.map(s => {
              const sev = SEV_BADGE[s.severidad ?? ""] ?? null;
              const pen = PEN_BADGE[s.penalidad ?? ""] ?? null;
              return (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold" style={{ color: INK }}>{s.empleado_nombre ?? `#${s.empleado}`}</td>
                  <td className="px-4 py-3 text-slate-500">{s.evento_nombre ?? "—"}</td>
                  <td className="max-w-xs truncate px-4 py-3 text-slate-500">{s.motivo}</td>
                  <td className="px-4 py-3">
                    {sev ? (
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${sev.bg} ${sev.text}`}>{s.severidad}</span>
                    ) : <span className="text-xs text-slate-300">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {pen ? (
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${pen.bg} ${pen.text}`}>{pen.label}</span>
                    ) : <span className="text-xs text-slate-300">Pendiente</span>}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">
                    {s.fecha_inicio && s.fecha_fin ? `${s.fecha_inicio} → ${s.fecha_fin}` : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">
                    {new Date(s.creado).toLocaleDateString("es-MX")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Modal nueva sanción */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={crear} className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Nueva sanción</h2>
            <p className="mb-4 text-xs text-slate-400">Los campos marcados * son obligatorios.</p>

            {error && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}

            <div className="space-y-3">
              {/* Empleado: escaneo QR o búsqueda manual */}
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label className="text-xs font-semibold text-slate-600">Empleado *</label>
                  <Ayuda>Persona sancionada. Escanea su gafete QR si lo lleva, o búscala por nombre. La sanción bloquea su acceso en el escáner según la penalidad.</Ayuda>
                </div>

                {form.empleado ? (
                  <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                    <span className="font-medium text-slate-700">{empLabel || `Empleado #${form.empleado}`}</span>
                    <button type="button" onClick={limpiarEmpleado} className="text-xs text-slate-400 hover:text-red-500">Cambiar</button>
                  </div>
                ) : (
                  <>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => { setScanError(null); setScanOpen(true); }}
                        className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <rect x="3" y="3" width="5" height="5"/><rect x="16" y="3" width="5" height="5"/><rect x="3" y="16" width="5" height="5"/>
                          <path d="M21 16h-3v3M18 21h3M21 19v-3M13 3v5h5M13 13h5v5M13 8v5M8 13H3"/>
                        </svg>
                        Escanear QR
                      </button>
                      <div className="relative flex-1">
                        <input value={empQuery} onChange={e => setEmpQuery(e.target.value)}
                          placeholder="Buscar empleado por nombre…"
                          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                        {(buscando || empSugs.length > 0) && empQuery.trim().length >= 2 && (
                          <ul className="absolute z-20 left-0 right-0 mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
                            {buscando && <li className="px-3 py-2 text-xs text-slate-400">Buscando…</li>}
                            {!buscando && empSugs.length === 0 && <li className="px-3 py-2 text-xs text-slate-400">Sin coincidencias.</li>}
                            {empSugs.map(o => (
                              <li key={o.id}>
                                <button type="button" onClick={() => seleccionarEmpleado(o)}
                                  className="w-full px-3 py-2 text-left text-sm hover:bg-blue-50">
                                  <span className="font-medium text-slate-800">{o.nombre}</span>
                                  {o.empresa && <span className="ml-1 text-xs text-slate-400">({o.empresa})</span>}
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-400">Escanea el gafete del empleado o escribe su nombre para buscarlo.</p>
                  </>
                )}
              </div>

              {/* Evento */}
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="san-evento" className="text-xs font-semibold text-slate-600">Evento</label>
                  <Ayuda>Evento en cuyo contexto ocurrió la falta. Se autocompleta si escaneas el gafete de un evento; puedes dejarlo vacío si no aplica.</Ayuda>
                </div>
                <select id="san-evento" value={F.evento} onChange={e => set("evento", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                  <option value="">Sin evento</option>
                  {eventos.map(ev => <option key={ev.id} value={ev.id}>{ev.nombre}</option>)}
                </select>
              </div>

              {esAdmin && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="san-severidad" className="text-xs font-semibold text-slate-600">Severidad</label>
                    <Ayuda>Gravedad de la falta (Bajo / Medio / Alto). Es informativa para el historial; no bloquea por sí sola el acceso — eso lo define la penalidad. Solo el administrador la define.</Ayuda>
                  </div>
                  <select id="san-severidad" value={F.severidad} onChange={e => set("severidad", e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    <option value="bajo">Bajo</option>
                    <option value="medio">Medio</option>
                    <option value="alto">Alto</option>
                  </select>
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="san-penalidad" className="text-xs font-semibold text-slate-600">Penalidad</label>
                    <Ayuda>Consecuencia aplicada. "Advertencia" no bloquea; "Suspensión" bloquea el acceso dentro del rango de fechas; "Baja" bloquea el acceso de forma permanente. Solo el administrador la define.</Ayuda>
                  </div>
                  <select id="san-penalidad" value={F.penalidad} onChange={e => set("penalidad", e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    <option value="advertencia">Advertencia</option>
                    <option value="suspension">Suspensión</option>
                    <option value="baja">Baja</option>
                  </select>
                </div>
              </div>
              )}

              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="san-motivo" className="text-xs font-semibold text-slate-600">Motivo *</label>
                  <Ayuda>Descripción del incidente que origina la sanción. Queda registrada en el historial del empleado.</Ayuda>
                </div>
                <textarea id="san-motivo" required rows={3} value={F.motivo} onChange={e => set("motivo", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 resize-none"
                  placeholder="Describe el motivo de la sanción…" />
              </div>

              {!esAdmin && (
                <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
                  La severidad y la penalidad las define un administrador después de registrar la amonestación.
                </p>
              )}

              {esAdmin && F.penalidad === "suspension" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="san-fi" className="text-xs font-semibold text-slate-600">Fecha inicio *</label>
                      <Ayuda>Primer día de la suspensión. Desde esta fecha el escáner deniega el acceso del empleado.</Ayuda>
                    </div>
                    <input id="san-fi" required type="date" value={F.fecha_inicio} onChange={e => set("fecha_inicio", e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                  </div>
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="san-ff" className="text-xs font-semibold text-slate-600">Fecha fin *</label>
                      <Ayuda>Último día de la suspensión. Después de esta fecha el empleado recupera el acceso automáticamente.</Ayuda>
                    </div>
                    <input id="san-ff" required type="date" value={F.fecha_fin} onChange={e => set("fecha_fin", e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: "#DC2626" }}>
                {saving ? "Guardando…" : "Registrar sanción"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal escáner QR */}
      {scanOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 px-4"
          onClick={() => setScanOpen(false)}>
          <div className="w-full max-w-sm rounded-modal bg-white p-5 shadow-panel" onClick={e => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-bold" style={{ color: INK }}>Escanear gafete</h3>
              <button onClick={() => setScanOpen(false)} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div id={QR_DIV_ID} className="mx-auto aspect-square w-full overflow-hidden rounded-lg bg-slate-900" />
            {scanError && <p className="mt-3 text-center text-sm font-medium text-red-600">{scanError}</p>}
            <p className="mt-3 text-center text-xs text-slate-400">Apunta la cámara al QR del gafete del empleado.</p>
          </div>
        </div>
      )}
    </div>
  );
}
