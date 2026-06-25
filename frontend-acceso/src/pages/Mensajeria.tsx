import { useEffect, useState } from "react";
import api from "../api/client";

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
interface Zona { id: number; nombre: string; recinto: number; }
interface Evento { id: number; nombre: string; }

const ESTADO_LABEL = ["Pendiente", "En progreso", "Cancelado", "Completado"];
const ESTADO_COLOR = [
  "bg-yellow-100 text-yellow-800",
  "bg-blue-100 text-blue-800",
  "bg-slate-100 text-slate-600",
  "bg-green-100 text-green-800",
];

const SEGMENTO_LABEL: Record<string, string> = {
  recinto: "Recinto",
  zona: "Zona",
  evento: "Evento",
  todos_eventos: "Todos los eventos",
  todos_recintos: "Todos los recintos",
  recintos_y_zonas: "Recintos y zonas",
};

const SEGMENTO_NECESITA_ID = ["recinto", "zona", "evento"];

export default function Mensajeria() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [recintos, setRecintos] = useState<Recinto[]>([]);
  const [zonas, setZonas] = useState<Zona[]>([]);
  const [eventos, setEventos] = useState<Evento[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ cuerpo: "", segmento: "todos_recintos", segmento_id: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const cargar = () =>
    Promise.all([
      api.get("/api/mensajeria/mensajes/"),
      api.get("/api/recintos/recintos/"),
      api.get("/api/recintos/zonas/"),
      api.get("/api/eventos/eventos/"),
    ]).then(([m, r, z, e]) => {
      setMensajes(m.data.results ?? m.data);
      setRecintos(r.data.results ?? r.data);
      setZonas(z.data.results ?? z.data);
      setEventos(e.data.results ?? e.data);
    }).finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      await api.post("/api/mensajeria/mensajes/", {
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
    if (form.segmento === "zona") return zonas;
    if (form.segmento === "evento") return eventos;
    return [];
  };

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Mensajería WhatsApp</h1>
        <button onClick={() => setShowForm(true)}
          className="ml-auto rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700">
          + Nueva campaña
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <form onSubmit={enviar} className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Nueva campaña WhatsApp</h2>
            {error && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Segmento de envío</label>
                <select value={form.segmento}
                  onChange={(e) => setForm({ ...form, segmento: e.target.value, segmento_id: "" })}
                  className="w-full rounded border px-2 py-1 text-sm">
                  {Object.entries(SEGMENTO_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>

              {SEGMENTO_NECESITA_ID.includes(form.segmento) && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600">
                    {SEGMENTO_LABEL[form.segmento]} específico
                  </label>
                  <select required value={form.segmento_id}
                    onChange={(e) => setForm({ ...form, segmento_id: e.target.value })}
                    className="w-full rounded border px-2 py-1 text-sm">
                    <option value="">Seleccionar…</option>
                    {opcionesPorSegmento().map((o) => (
                      <option key={o.id} value={o.id}>{o.nombre}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600">Mensaje</label>
                <textarea required rows={4} value={form.cuerpo}
                  onChange={(e) => setForm({ ...form, cuerpo: e.target.value })}
                  className="w-full rounded border px-2 py-1 text-sm"
                  placeholder="Hola {nombre}, te informamos que…" />
                <p className="mt-0.5 text-xs text-slate-400">{form.cuerpo.length} caracteres</p>
              </div>

              <div className="rounded bg-amber-50 p-3 text-xs text-amber-800">
                El mensaje se enviará por WhatsApp (UltraMsg) a todos los empleados activos
                del segmento seleccionado que tengan número de teléfono registrado.
              </div>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)}
                className="rounded border px-4 py-1 text-sm">Cancelar</button>
              <button type="submit" disabled={saving}
                className="rounded bg-green-600 px-4 py-1 text-sm text-white disabled:opacity-50">
                {saving ? "Enviando…" : "Enviar campaña"}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-slate-500">Cargando…</p>
      ) : mensajes.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center text-slate-400 shadow-sm">
          <p>No hay campañas enviadas aún.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {mensajes.map((m) => (
            <div key={m.id} className="rounded-xl border bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex-1">
                  <p className="text-sm text-slate-800">{m.cuerpo}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {SEGMENTO_LABEL[m.segmento] ?? m.segmento}
                    {m.segmento_id ? ` #${m.segmento_id}` : ""}
                    {" · "}
                    {m.total_destinatarios} destinatario{m.total_destinatarios !== 1 ? "s" : ""}
                    {" · "}
                    {new Date(m.creado).toLocaleString("es-MX")}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_COLOR[m.estado] ?? "bg-slate-100"}`}>
                    {ESTADO_LABEL[m.estado] ?? m.estado}
                  </span>
                  {m.estado === 1 && (
                    <div className="w-32">
                      <div className="h-1.5 w-full rounded-full bg-slate-200">
                        <div
                          className="h-1.5 rounded-full bg-green-500 transition-all"
                          style={{ width: `${Math.round(m.progreso * 100)}%` }}
                        />
                      </div>
                      <p className="mt-0.5 text-right text-xs text-slate-400">
                        {Math.round(m.progreso * 100)}%
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
