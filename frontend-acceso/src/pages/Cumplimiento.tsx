/**
 * Cumplimiento SAT 69-B — módulo del sidebar (admin).
 * Valida que ningún proveedor esté en la lista 69-B del SAT; si alguno aparece, lo alerta.
 * Muestra el estado del padrón, permite revalidar a todos y lista los proveedores marcados.
 */
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

interface ProveedorMarcado {
  id: number; nombre: string; rfc: string | null; situacion: string | null;
}
interface Resumen {
  total_efos: number;
  ultima_actualizacion: string | null;
  padron_cargado: boolean;
  importando: boolean;
  marcados: number;
  proveedores: ProveedorMarcado[];
}

interface EfoRow {
  id: number; rfc: string; nombre: string | null; situacion: string;
}

const INK = "#0F1B2D";

// Color de la situación en el padrón: Definitivo = firme (peor), Presunto = en proceso,
// Desvirtuado / Sentencia Favorable = ya no representa riesgo.
const SITUACION_BADGE: Record<string, { bg: string; text: string }> = {
  "Definitivo":          { bg: "bg-red-100",    text: "text-red-700"   },
  "Presunto":            { bg: "bg-amber-100",  text: "text-amber-700" },
  "Desvirtuado":         { bg: "bg-slate-100",  text: "text-slate-600" },
  "Sentencia Favorable": { bg: "bg-green-100",  text: "text-green-700" },
};

export default function Cumplimiento() {
  const navigate = useNavigate();
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [cargando, setCargando] = useState(true);
  const [revalidando, setRevalidando] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // Buscador del padrón completo 69-B (cualquier RFC/razón social, sea o no proveedor del tenant).
  const [q, setQ] = useState("");
  const [situacionFiltro, setSituacionFiltro] = useState("");
  const [resultados, setResultados] = useState<EfoRow[]>([]);
  const [total, setTotal] = useState(0);
  const [buscando, setBuscando] = useState(false);

  const cargar = useCallback(() => {
    setCargando(true);
    api.get<Resumen>("/api/cumplimiento/resumen/")
      .then(r => setResumen(r.data))
      .catch(() => setResumen(null))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  // Búsqueda con debounce (mínimo 2 caracteres). Sin término y sin filtro, no consulta.
  useEffect(() => {
    const term = q.trim();
    if (term.length < 2 && !situacionFiltro) {
      setResultados([]); setTotal(0); setBuscando(false);
      return;
    }
    setBuscando(true);
    const t = setTimeout(() => {
      const params = new URLSearchParams();
      if (term.length >= 2) params.set("search", term);
      if (situacionFiltro)  params.set("situacion", situacionFiltro);
      api.get<{ count: number; results: EfoRow[] }>(`/api/cumplimiento/efos/?${params}`)
        .then(r => { setResultados(r.data.results ?? []); setTotal(r.data.count ?? 0); })
        .catch(() => { setResultados([]); setTotal(0); })
        .finally(() => setBuscando(false));
    }, 350);
    return () => clearTimeout(t);
  }, [q, situacionFiltro]);

  async function revalidar() {
    setRevalidando(true); setMsg(null);
    try {
      const { data } = await api.post<{ revisados: number; encontrados: number }>("/api/cumplimiento/revalidar/");
      setMsg(`Revalidados ${data.revisados} proveedores · ${data.encontrados} en la lista 69-B.`);
      cargar();
    } catch {
      setMsg("No se pudo revalidar. Intenta de nuevo.");
    } finally {
      setRevalidando(false);
    }
  }

  const fmt = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
          <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M9 12l2 2 4-4"/><path d="M12 3l7 4v5c0 4-3 7-7 9-4-2-7-5-7-9V7z"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Cumplimiento SAT 69-B</h1>
          <p className="text-xs text-slate-500">Validación de proveedores contra el padrón de EFOS del SAT</p>
        </div>
        <button onClick={revalidar} disabled={revalidando}
          className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
          style={{ backgroundColor: "#2563EB" }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
          {revalidando ? "Revalidando…" : "Revalidar proveedores"}
        </button>
      </div>

      {msg && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">{msg}</div>
      )}

      {/* Estado del padrón */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-card bg-white p-5 shadow-card">
          <p className="text-[12px] font-semibold uppercase tracking-widest text-slate-400">RFCs en el padrón</p>
          <p className="mt-1 text-[28px] font-extrabold tabular leading-none" style={{ color: INK }}>
            {cargando ? "…" : (resumen?.total_efos ?? 0).toLocaleString("es-MX")}
          </p>
        </div>
        <div className="rounded-card bg-white p-5 shadow-card">
          <p className="text-[12px] font-semibold uppercase tracking-widest text-slate-400">Última actualización</p>
          <p className="mt-1 text-sm font-semibold text-slate-600">{cargando ? "…" : fmt(resumen?.ultima_actualizacion ?? null)}</p>
        </div>
        <div className={`rounded-card p-5 shadow-card ${resumen && resumen.marcados > 0 ? "bg-[#FEF2F2]" : "bg-[#F0FDF4]"}`}>
          <p className="text-[12px] font-semibold uppercase tracking-widest text-slate-400">Proveedores marcados</p>
          <p className={`mt-1 text-[28px] font-extrabold tabular leading-none ${resumen && resumen.marcados > 0 ? "text-[#DC2626]" : "text-[#16A34A]"}`}>
            {cargando ? "…" : (resumen?.marcados ?? 0)}
          </p>
        </div>
      </div>

      {/* Padrón aún vacío: se actualiza solo (auto-import en background + sincronización mensual). */}
      {resumen && !resumen.padron_cargado && (
        <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          <svg className="h-4 w-4 flex-shrink-0 animate-spin" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M21 12a9 9 0 11-6.219-8.56" />
          </svg>
          El padrón del SAT se está actualizando automáticamente. En unos minutos verás aquí la
          validación de tus proveedores; el sistema lo mantiene al día por ti (sin acción manual).
        </div>
      )}

      {/* Alerta / lista de proveedores en la 69-B */}
      {resumen && resumen.marcados > 0 ? (
        <div className="overflow-hidden rounded-card border border-red-200 bg-white shadow-card">
          <div className="flex items-center gap-2 border-b border-red-100 bg-[#FEF2F2] px-5 py-3">
            <svg className="h-5 w-5 text-red-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <p className="text-sm font-bold text-red-700">
              {resumen.marcados} proveedor{resumen.marcados !== 1 ? "es" : ""} aparece{resumen.marcados !== 1 ? "n" : ""} en la lista 69-B del SAT
            </p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-5 py-2.5">Proveedor</th>
                <th className="px-5 py-2.5">RFC</th>
                <th className="px-5 py-2.5">Situación SAT</th>
                <th className="px-5 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {resumen.proveedores.map(p => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3 font-semibold" style={{ color: INK }}>{p.nombre}</td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-600">{p.rfc ?? "—"}</td>
                  <td className="px-5 py-3">
                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-700">
                      {p.situacion ?? "—"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button onClick={() => navigate("/proveedores")}
                      className="text-xs font-medium" style={{ color: "#2563EB" }}>Ver proveedor</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : resumen && resumen.padron_cargado && !cargando ? (
        <div className="flex items-center gap-2 rounded-card bg-[#F0FDF4] px-5 py-4 text-sm font-medium text-green-700 shadow-card">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/></svg>
          Ningún proveedor aparece en la lista 69-B del SAT.
        </div>
      ) : null}

      {/* Buscador del padrón completo 69-B (cualquier RFC/razón social) */}
      <div className="rounded-card bg-white p-5 shadow-card">
        <h2 className="text-sm font-bold" style={{ color: INK }}>Buscar en el listado completo</h2>
        <p className="mt-0.5 text-xs text-slate-500">
          Verifica a cualquier contribuyente en el padrón 69-B del SAT, esté o no dado de alta como
          proveedor. Busca por RFC o razón social (mínimo 2 caracteres).
        </p>

        <div className="mt-4 flex flex-wrap gap-3">
          <div className="relative min-w-[16rem] flex-1">
            <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
            </svg>
            <input
              className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              placeholder="RFC o razón social…"
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <select
            className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-600 outline-none focus:border-blue-400"
            value={situacionFiltro}
            onChange={e => setSituacionFiltro(e.target.value)}
            title="Situación"
          >
            <option value="">Todas las situaciones</option>
            <option value="Definitivo">Definitivo</option>
            <option value="Presunto">Presunto</option>
            <option value="Desvirtuado">Desvirtuado</option>
            <option value="Sentencia Favorable">Sentencia Favorable</option>
          </select>
        </div>

        {/* Resultados */}
        <div className="mt-4">
          {buscando ? (
            <div className="flex items-center justify-center py-10">
              <div className="h-7 w-7 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
            </div>
          ) : q.trim().length < 2 && !situacionFiltro ? (
            <p className="py-8 text-center text-sm text-slate-400">Escribe un RFC o razón social para buscar en el padrón.</p>
          ) : resultados.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">Sin coincidencias en el padrón 69-B.</p>
          ) : (
            <>
              <div className="overflow-x-auto rounded-xl ring-1 ring-slate-100">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                      <th className="px-4 py-2.5">RFC</th>
                      <th className="px-4 py-2.5">Razón social</th>
                      <th className="px-4 py-2.5">Situación</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {resultados.map(e => {
                      const badge = SITUACION_BADGE[e.situacion] ?? { bg: "bg-slate-100", text: "text-slate-600" };
                      return (
                        <tr key={e.id} className="hover:bg-slate-50">
                          <td className="px-4 py-2.5 font-mono text-xs text-slate-700">{e.rfc}</td>
                          <td className="px-4 py-2.5 text-slate-700">{e.nombre || "—"}</td>
                          <td className="px-4 py-2.5">
                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.bg} ${badge.text}`}>
                              {e.situacion}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-right text-xs text-slate-400">
                {total.toLocaleString("es-MX")} coincidencia{total !== 1 ? "s" : ""}
                {total > resultados.length ? ` · mostrando ${resultados.length}` : ""}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
