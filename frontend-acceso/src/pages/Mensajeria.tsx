import { useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

interface Mensaje {
  id: number;
  cuerpo: string;
  segmento: string;
  segmento_id: number | null;
  estado: number;
  progreso: number;
  creado: string;
  total_destinatarios: number;
}

interface Recinto { id: number; nombre: string; }
interface Zona    { id: number; nombre: string; recinto: number; }
interface Evento  { id: number; nombre: string; }

const INK    = "#0F1B2D";
const WA_GREEN = "#25D366";

const ESTADO_BADGE = [
  { bg: "bg-amber-100",  text: "text-amber-800",  label: "Pendiente"    },
  { bg: "bg-blue-100",   text: "text-blue-800",   label: "En progreso"  },
  { bg: "bg-slate-100",  text: "text-slate-600",  label: "Cancelado"    },
  { bg: "bg-green-100",  text: "text-green-800",  label: "Completado"   },
];

const SEGMENTO_LABEL: Record<string, string> = {
  recinto:         "Recinto",
  zona:            "Zona",
  evento:          "Evento",
  todos_eventos:   "Todos los eventos",
  todos_recintos:  "Todos los recintos",
  recintos_y_zonas:"Recintos y zonas",
};

const SEGMENTO_NECESITA_ID = ["recinto", "zona", "evento"];

function fmtFecha(iso: string) {
  return new Date(iso).toLocaleString("es-MX", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export default function Mensajeria() {
  const [mensajes,  setMensajes]  = useState<Mensaje[]>([]);
  const [recintos,  setRecintos]  = useState<Recinto[]>([]);
  const [zonas,     setZonas]     = useState<Zona[]>([]);
  const [eventos,   setEventos]   = useState<Evento[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [form,      setForm]      = useState({ cuerpo: "", segmento: "todos_recintos", segmento_id: "" });
  const [saving,    setSaving]    = useState(false);
  const [error,     setError]     = useState("");

  const cargar = () =>
    Promise.all([
      api.get("/api/mensajes/"),
      api.get("/api/recintos/"),
      api.get("/api/zonas/"),
      api.get("/api/eventos/"),
    ]).then(([m, r, z, e]) => {
      setMensajes(m.data.results ?? m.data);
      setRecintos(r.data.results ?? r.data);
      setZonas(z.data.results ?? z.data);
      setEventos(e.data.results ?? e.data);
    }).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await api.post("/api/mensajes/", {
        cuerpo: form.cuerpo,
        segmento: form.segmento,
        segmento_id: SEGMENTO_NECESITA_ID.includes(form.segmento) && form.segmento_id
          ? Number(form.segmento_id) : null,
      });
      setShowForm(false);
      setForm({ cuerpo: "", segmento: "todos_recintos", segmento_id: "" });
      cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error"));
    } finally { setSaving(false); }
  };

  const opcionesPorSegmento = () => {
    if (form.segmento === "recinto") return recintos;
    if (form.segmento === "zona")    return zonas;
    if (form.segmento === "evento")  return eventos;
    return [];
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{ backgroundColor: "#F0FDF4" }}>
          {/* WhatsApp icon */}
          <svg className="h-5 w-5" style={{ color: "#16A34A" }} viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.521.149-.174.198-.298.298-.497.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.5-.669-.51-.173-.008-.372-.01-.571-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Mensajería</h1>
          <p className="text-xs text-slate-500">Campañas por WhatsApp (UltraMsg)</p>
        </div>
        <button onClick={() => { setError(""); setShowForm(true); }}
          className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: WA_GREEN }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nueva campaña
        </button>
      </div>

      {/* Lista de mensajes */}
      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-20 animate-pulse rounded-card bg-slate-100" />)}
        </div>
      ) : mensajes.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-card bg-white py-16 shadow-card text-center">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
            <svg className="h-7 w-7 text-slate-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
          </div>
          <p className="text-sm font-medium text-slate-400">No hay campañas enviadas aún.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {mensajes.map(m => {
            const badge = ESTADO_BADGE[m.estado] ?? ESTADO_BADGE[0];
            return (
              <div key={m.id} className="rounded-card bg-white p-5 shadow-card">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="mb-2 text-sm leading-relaxed" style={{ color: INK }}>{m.cuerpo}</p>
                    <div className="flex flex-wrap gap-x-4 gap-y-1">
                      <span className="text-xs text-slate-400">
                        Segmento: <span className="font-medium text-slate-600">{SEGMENTO_LABEL[m.segmento] ?? m.segmento}</span>
                      </span>
                      <span className="tabular text-xs text-slate-400">
                        Destinatarios: <span className="font-medium text-slate-600">{m.total_destinatarios}</span>
                      </span>
                      <span className="tabular font-mono text-xs text-slate-400">{fmtFecha(m.creado)}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.bg} ${badge.text}`}>
                      {badge.label}
                    </span>
                    {m.estado === 1 && (
                      <div className="w-32">
                        <div className="h-1.5 w-full rounded-full bg-slate-200">
                          <div
                            className="h-1.5 rounded-full bg-green-500 transition-all"
                            style={{ width: `${Math.round(m.progreso * 100)}%` }}
                          />
                        </div>
                        <p className="tabular mt-0.5 text-right font-mono text-xs text-slate-400">
                          {Math.round(m.progreso * 100)}%
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal nueva campaña */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={enviar} className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Nueva campaña WhatsApp</h2>
            <p className="mb-4 text-xs text-slate-400">El mensaje se enviará por UltraMsg a los destinatarios del segmento.</p>

            {error && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}

            <div className="space-y-3">
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="msg-segmento" className="text-xs font-semibold text-slate-600">Segmento de envío *</label>
                  <Ayuda>Define quiénes reciben la campaña: un recinto, una zona, un evento concreto, o grupos amplios (todos los recintos/eventos). Solo empleados activos con teléfono registrado.</Ayuda>
                </div>
                <select id="msg-segmento" value={form.segmento}
                  onChange={e => setForm({ ...form, segmento: e.target.value, segmento_id: "" })}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                  {Object.entries(SEGMENTO_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>

              {SEGMENTO_NECESITA_ID.includes(form.segmento) && (
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="msg-segid" className="text-xs font-semibold text-slate-600">
                      {SEGMENTO_LABEL[form.segmento]} específico *
                    </label>
                    <Ayuda>Elemento concreto del segmento elegido al que se dirige la campaña.</Ayuda>
                  </div>
                  <select id="msg-segid" required value={form.segmento_id}
                    onChange={e => setForm({ ...form, segmento_id: e.target.value })}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    <option value="">Seleccionar…</option>
                    {opcionesPorSegmento().map(o => (
                      <option key={o.id} value={o.id}>{o.nombre}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-600">
                  <div className="flex items-center gap-1.5">
                    <label htmlFor="msg-cuerpo">Mensaje *</label>
                    <Ayuda>Texto que se envía por WhatsApp. Puedes usar {"{nombre}"} para personalizar con el nombre de cada destinatario.</Ayuda>
                  </div>
                  <span className="font-normal text-slate-400">{form.cuerpo.length} chars</span>
                </div>
                <textarea id="msg-cuerpo" required rows={4} value={form.cuerpo}
                  onChange={e => setForm({ ...form, cuerpo: e.target.value })}
                  className="w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  placeholder="Hola {nombre}, te informamos que…" />
              </div>

              <div className="rounded-lg bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
                Solo empleados activos del segmento con teléfono registrado recibirán el mensaje.
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: WA_GREEN }}>
                {saving ? "Enviando…" : "Enviar campaña"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
