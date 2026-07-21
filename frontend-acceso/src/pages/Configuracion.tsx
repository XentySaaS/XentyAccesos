import { useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

const INK = "#0F1B2D";
const SIGNAL = "#2563EB";

// Ajustes del sistema por tenant. Pensado para crecer: cada área de configuración es una pestaña;
// hoy solo "Retención de bitácoras", pero aquí entrarán las que vengan (notificaciones, marca, etc.).
type Tab = "retencion";

function inp(err?: string) {
  return `w-full rounded-xl border px-3 py-2 text-sm outline-none transition focus:ring-2 ${
    err ? "border-red-300 focus:ring-red-100" : "border-slate-200 focus:border-blue-400 focus:ring-blue-100"
  }`;
}
function Err({ msg }: { msg?: string }) {
  return msg ? <p className="mt-1 text-[11px] text-red-500">{msg}</p> : null;
}

// ── Retención de bitácoras ──────────────────────────────────────────────────
function Retencion() {
  const [hist,    setHist]    = useState("");
  const [bita,    setBita]    = useState("");
  const [defHist, setDefHist] = useState(365);
  const [defBita, setDefBita] = useState(365);
  const [loading, setLoading] = useState(true);
  const [saving,  setSaving]  = useState(false);
  const [errs,    setErrs]    = useState<Record<string, string>>({});
  const [msg,     setMsg]     = useState<{ ok: boolean; texto: string } | null>(null);

  useEffect(() => {
    api.get("/api/config/retencion/")
      .then(r => {
        setHist(String(r.data.historial.dias));
        setBita(String(r.data.bitacora.dias));
        setDefHist(r.data.historial.default);
        setDefBita(r.data.bitacora.default);
      })
      .finally(() => setLoading(false));
  }, []);

  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setErrs({}); setMsg(null);
    try {
      const { data } = await api.put("/api/config/retencion/", {
        historial_dias: hist === "" ? undefined : Number(hist),
        bitacora_dias:  bita === "" ? undefined : Number(bita),
      });
      setHist(String(data.historial.dias));
      setBita(String(data.bitacora.dias));
      setMsg({ ok: true, texto: "Retención guardada. Se aplica en la próxima purga diaria." });
    } catch (err: any) {
      setErrs(err?.response?.data ?? {});
      setMsg({ ok: false, texto: "Revisa los valores." });
    } finally { setSaving(false); }
  }

  if (loading) return <div className="py-12 text-center"><div className="mx-auto h-7 w-7 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"/></div>;

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-slate-500">
        Cuánto tiempo se conservan las bitácoras antes de borrarse automáticamente. Una purga diaria
        libera almacenamiento; escribe <strong>0</strong> para conservar sin límite.
      </p>
      {msg && (
        <div className={`mb-4 rounded-lg px-4 py-2.5 text-sm ring-1 ${msg.ok ? "bg-green-50 text-green-700 ring-green-100" : "bg-red-50 text-red-700 ring-red-100"}`}>
          {msg.texto}
        </div>
      )}
      <form onSubmit={guardar} className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div>
          <div className="mb-1 flex items-center gap-1.5">
            <label htmlFor="ret-hist" className="text-xs font-semibold text-slate-600">Historial de cambios (días)</label>
            <Ayuda>Días que se conserva el Historial de cambios (quién creó / editó / eliminó datos) antes de borrar lo más antiguo. 0 = conservar sin límite.</Ayuda>
          </div>
          <input id="ret-hist" type="number" min={0} max={3650} inputMode="numeric"
            value={hist} onChange={e => setHist(e.target.value.replace(/\D/g, ""))}
            className={inp(errs.historial_dias)} />
          <p className="mt-1 text-[11px] text-slate-400">Por defecto: {defHist} días.</p>
          <Err msg={errs.historial_dias} />
        </div>
        <div>
          <div className="mb-1 flex items-center gap-1.5">
            <label htmlFor="ret-bita" className="text-xs font-semibold text-slate-600">Accesos al sistema (días)</label>
            <Ayuda>Días que se conserva la bitácora de Accesos al sistema (inicios/cierres de sesión e intentos fallidos, con IP y dispositivo). 0 = conservar sin límite.</Ayuda>
          </div>
          <input id="ret-bita" type="number" min={0} max={3650} inputMode="numeric"
            value={bita} onChange={e => setBita(e.target.value.replace(/\D/g, ""))}
            className={inp(errs.bitacora_dias)} />
          <p className="mt-1 text-[11px] text-slate-400">Por defecto: {defBita} días.</p>
          <Err msg={errs.bitacora_dias} />
        </div>
        <div className="flex justify-end pt-2">
          <button type="submit" disabled={saving} className="rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: SIGNAL }}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────
const TABS: { id: Tab; label: string }[] = [
  { id: "retencion", label: "Retención de bitácoras" },
];

export default function Configuracion() {
  const [tab, setTab] = useState<Tab>("retencion");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Configuración</h1>
        <p className="mt-0.5 text-sm text-slate-500">Ajustes del sistema para este recinto.</p>
      </div>

      {/* Pestañas: crecen conforme se agreguen más áreas de configuración. */}
      <div className="mb-6 flex w-fit gap-1 rounded-xl border border-slate-200 bg-white p-1">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              tab === t.id
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "retencion" && <Retencion />}
    </div>
  );
}
