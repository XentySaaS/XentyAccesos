/**
 * Accesos — bitácora operativa de entradas y salidas.
 *
 * Muestra RegistroAcceso filtrado por fecha y tipo.
 * Acción: registrar salida (POST /api/acceso/registros/{id}/salida/).
 */
import { useCallback, useEffect, useState } from "react";
import api from "../api/client";

/* ── Tipos ──────────────────────────────────────────────────────────────── */
interface RegistroAcceso {
  id: number;
  tipo_acceso: "entrada" | "denegado";
  metodo: "qr" | "placa" | "manual" | "tarjeta";
  hora_entrada: string;
  hora_salida: string | null;
  placa_vehiculo: string | null;
  observaciones: string | null;
  persona: string;
  titulo: string;
  tipo_registro: "cita" | "evento" | "manual";
}

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const METODO_LABEL: Record<string, string> = {
  qr: "QR", placa: "Placa", manual: "Manual", tarjeta: "Tarjeta",
};
const METODO_COLOR: Record<string, string> = {
  qr:      "bg-blue-50 text-blue-700",
  placa:   "bg-violet-50 text-violet-700",
  manual:  "bg-slate-100 text-slate-600",
  tarjeta: "bg-teal-50 text-teal-700",
};
const TIPO_REG_LABEL: Record<string, string> = {
  cita: "Cita", evento: "Evento", manual: "Manual",
};

function lista<T>(d: { results?: T[] } | T[]): T[] {
  return Array.isArray(d) ? d : (d.results ?? []);
}

function hoy() { return new Date().toISOString().split("T")[0]; }

function fmtHora(iso: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}
function fmtFecha(iso: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}
function mismoDia(a: string, b: string) {
  if (!a || !b) return false;
  const da = new Date(a), db = new Date(b);
  return da.toDateString() === db.toDateString();
}

/* ── Opciones de filtro de fecha ─────────────────────────────────────── */
type RangoFecha = "hoy" | "ayer" | "semana" | "todo";

function rangoFechas(r: RangoFecha): { desde: string; hasta: string } | null {
  const ahora = new Date();
  const fmt = (d: Date) => d.toISOString().split("T")[0];
  const resta = (d: number) => { const x = new Date(ahora); x.setDate(x.getDate() - d); return fmt(x); };
  if (r === "hoy")    return { desde: hoy(), hasta: hoy() };
  if (r === "ayer")   return { desde: resta(1), hasta: resta(1) };
  if (r === "semana") return { desde: resta(6), hasta: hoy() };
  return null;
}

/* ══════════════════════════════════════════════════════════════════════════
   Página principal
   ══════════════════════════════════════════════════════════════════════════ */
export default function Accesos() {
  const [registros,  setRegistros]  = useState<RegistroAcceso[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [filtroTipo, setFiltroTipo] = useState("");
  const [rango,      setRango]      = useState<RangoFecha>("hoy");
  const [saliendo,   setSaliendo]   = useState<number | null>(null);

  const cargar = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (filtroTipo) params.tipo_acceso = filtroTipo;
    const fechas = rangoFechas(rango);
    if (fechas) { params.fecha_desde = fechas.desde; params.fecha_hasta = fechas.hasta; }
    api.get("/api/acceso/registros/", { params })
      .then(r => setRegistros(lista(r.data)))
      .finally(() => setLoading(false));
  }, [filtroTipo, rango]);

  useEffect(() => { cargar(); }, [cargar]);

  const registrarSalida = async (id: number) => {
    setSaliendo(id);
    try {
      await api.post(`/api/acceso/registros/${id}/salida/`);
      cargar();
    } finally { setSaliendo(null); }
  };

  const enRecinto = registros.filter(
    r => r.tipo_acceso === "entrada" && !r.hora_salida
  ).length;

  /* ── Render ───────────────────────────────────────────────── */
  return (
    <div>
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-50">
          <svg className="h-5 w-5 text-green-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Accesos</h1>
          <p className="text-xs text-slate-500">Bitácora de entradas y salidas</p>
        </div>

        {/* Contador en recinto */}
        {enRecinto > 0 && (
          <div className="flex items-center gap-1.5 rounded-lg bg-green-50 px-3 py-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
            </span>
            <span className="text-xs font-semibold text-green-700">{enRecinto} en recinto</span>
          </div>
        )}

        {/* Filtro rango */}
        <div className="flex overflow-hidden rounded-lg border border-slate-200 bg-white text-xs font-semibold">
          {(["hoy", "ayer", "semana", "todo"] as RangoFecha[]).map(r => (
            <button key={r} onClick={() => setRango(r)}
              className={`px-3 py-2 transition-colors ${rango === r ? "text-white" : "text-slate-500 hover:bg-slate-50"}`}
              style={rango === r ? { backgroundColor: SIGNAL } : {}}>
              {r === "hoy" ? "Hoy" : r === "ayer" ? "Ayer" : r === "semana" ? "7 días" : "Todo"}
            </button>
          ))}
        </div>

        {/* Filtro tipo */}
        <select value={filtroTipo} onChange={e => setFiltroTipo(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 outline-none focus:border-blue-400">
          <option value="">Todos</option>
          <option value="entrada">Entradas</option>
          <option value="denegado">Denegados</option>
        </select>

        <button onClick={cargar}
          className="rounded-lg border border-slate-200 p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
        </button>
      </div>

      {/* ── Tabla ─────────────────────────────────────────────── */}
      <div className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50 text-left">
                {["Persona", "Tipo", "Método", "Cita / Evento", "Fecha", "Entrada", "Salida", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {loading && (
                <tr><td colSpan={8} className="px-4 py-10">
                  <div className="space-y-2">{[1,2,3,4].map(i =>
                    <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />
                  )}</div>
                </td></tr>
              )}
              {!loading && registros.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-14 text-center">
                  <svg className="mx-auto mb-3 h-8 w-8 text-slate-200" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                    <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>
                  </svg>
                  <p className="text-sm font-medium text-slate-400">Sin registros de acceso</p>
                  <p className="mt-0.5 text-xs text-slate-300">
                    {rango === "hoy" ? "No hubo accesos hoy." : "Prueba cambiar el filtro de fecha."}
                  </p>
                </td></tr>
              )}
              {!loading && registros.map(r => {
                const esEntrada = r.tipo_acceso === "entrada";
                const sinSalida = esEntrada && !r.hora_salida;
                return (
                  <tr key={r.id} className={`hover:bg-slate-50 ${sinSalida ? "bg-green-50/40" : ""}`}>
                    {/* Persona */}
                    <td className="px-4 py-3">
                      <p className="font-semibold" style={{ color: INK }}>{r.persona}</p>
                      {r.placa_vehiculo && (
                        <p className="text-xs text-slate-400">Placa: {r.placa_vehiculo}</p>
                      )}
                    </td>

                    {/* Tipo acceso */}
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                        esEntrada ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
                      }`}>
                        {esEntrada ? (
                          <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                            <path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/>
                          </svg>
                        ) : (
                          <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                          </svg>
                        )}
                        {esEntrada ? "Entrada" : "Denegado"}
                      </span>
                    </td>

                    {/* Método */}
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold ${METODO_COLOR[r.metodo] ?? "bg-slate-100 text-slate-500"}`}>
                        {METODO_LABEL[r.metodo] ?? r.metodo}
                      </span>
                    </td>

                    {/* Cita / Evento */}
                    <td className="px-4 py-3">
                      <p className="max-w-[160px] truncate text-sm font-medium" style={{ color: INK }}>
                        {r.titulo}
                      </p>
                      <p className="text-xs text-slate-400">{TIPO_REG_LABEL[r.tipo_registro] ?? "—"}</p>
                    </td>

                    {/* Fecha del registro */}
                    <td className="px-4 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
                      {fmtFecha(r.hora_entrada)}
                    </td>

                    {/* Hora entrada */}
                    <td className="px-4 py-3 font-mono text-xs text-slate-600 whitespace-nowrap">
                      {fmtHora(r.hora_entrada)}
                    </td>

                    {/* Hora salida (si cae otro día, se indica la fecha para no confundir) */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      {r.hora_salida ? (
                        <span className="font-mono text-xs text-slate-600">
                          {!mismoDia(r.hora_entrada, r.hora_salida) && (
                            <span className="mr-1 text-slate-400">{fmtFecha(r.hora_salida)}</span>
                          )}
                          {fmtHora(r.hora_salida)}
                        </span>
                      ) : esEntrada ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-green-600">
                          <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                          </span>
                          En recinto
                        </span>
                      ) : (
                        <span className="text-xs text-slate-300">—</span>
                      )}
                    </td>

                    {/* Acción */}
                    <td className="px-4 py-3 text-right">
                      {sinSalida && (
                        <button onClick={() => registrarSalida(r.id)} disabled={saliendo === r.id}
                          className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700 disabled:opacity-50 whitespace-nowrap">
                          {saliendo === r.id ? "…" : "Registrar salida"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer con total */}
        {!loading && registros.length > 0 && (
          <div className="border-t border-slate-100 px-4 py-2.5 text-right text-xs text-slate-400">
            {registros.length} {registros.length === 1 ? "registro" : "registros"}
            {filtroTipo && ` · filtrando por ${filtroTipo}`}
          </div>
        )}
      </div>
    </div>
  );
}
