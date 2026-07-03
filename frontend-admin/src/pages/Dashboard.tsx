import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";

interface Tenant {
  id: number;
  schema_name: string;
  nombre: string;
  estado: string;
  trial_ends_at: string | null;
  modo_solo_lectura: boolean;
  gracia_hasta: string | null;
  plan: string | null;
  saldo: number;
}

interface Pagina { results?: Tenant[]; }

const INK = "#0F1B2D";

const ESTADOS: { key: string; label: string; color: string }[] = [
  { key: "trial",      label: "Trial",      color: "#2563EB" },
  { key: "activo",     label: "Activos",    color: "#16A34A" },
  { key: "suspendido", label: "Suspendidos", color: "#D97706" },
  { key: "cancelado",  label: "Cancelados", color: "#DC2626" },
];

const DIA_MS = 24 * 60 * 60 * 1000;

function diasRestantes(iso: string | null): number | null {
  if (!iso) return null;
  return Math.ceil((new Date(iso).getTime() - Date.now()) / DIA_MS);
}

export default function Dashboard() {
  const [items, setItems]     = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Pagina | Tenant[]>("/api/admin/tenants/");
        setItems(Array.isArray(data) ? data : data.results ?? []);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const m = useMemo(() => {
    const porEstado: Record<string, number> = {};
    const porPlan: Record<string, number> = {};
    let creditos = 0;
    let soloLectura = 0;
    let enGracia = 0;
    const ahora = Date.now();
    for (const t of items) {
      porEstado[t.estado] = (porEstado[t.estado] ?? 0) + 1;
      const plan = t.plan ?? "Sin plan";
      porPlan[plan] = (porPlan[plan] ?? 0) + 1;
      creditos += t.saldo;
      if (t.modo_solo_lectura) soloLectura += 1;
      if (t.gracia_hasta && new Date(t.gracia_hasta).getTime() > ahora) enGracia += 1;
    }
    // Trials que vencen en los próximos 14 días (o ya vencidos), más urgentes primero.
    const trialsPorVencer = items
      .filter((t) => t.estado === "trial" && t.trial_ends_at)
      .map((t) => ({ t, dias: diasRestantes(t.trial_ends_at)! }))
      .filter((x) => x.dias <= 14)
      .sort((a, b) => a.dias - b.dias);
    return { porEstado, porPlan, creditos, soloLectura, enGracia, trialsPorVencer };
  }, [items]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  const total = items.length;
  const planes = Object.entries(m.porPlan).sort((a, b) => b[1] - a[1]);
  const maxPlan = planes.reduce((mx, [, n]) => Math.max(mx, n), 1);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Control plane</h1>
        <p className="mt-0.5 text-sm text-slate-500">Resumen de la suite · tenants, suscripciones y consumo.</p>
      </div>

      {/* KPIs principales */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Kpi label="Tenants" valor={total} tono="text-slate-800" />
        <Kpi label="Activos" valor={m.porEstado["activo"] ?? 0} tono="text-green-700" />
        <Kpi label="En gracia" valor={m.enGracia} tono={m.enGracia ? "text-green-700" : "text-slate-800"} nota="acceso manual vigente" />
        <Kpi label="En solo lectura" valor={m.soloLectura} tono={m.soloLectura ? "text-amber-700" : "text-slate-800"} nota="dunning / retención" />
        <Kpi label="Créditos totales" valor={m.creditos} tono="text-slate-800" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Distribución por estado */}
        <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Por estado</h2>
          <div className="mt-4 space-y-3">
            {ESTADOS.map((e) => {
              const n = m.porEstado[e.key] ?? 0;
              const pct = total ? Math.round((n / total) * 100) : 0;
              return (
                <div key={e.key}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="flex items-center gap-2 text-slate-600">
                      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: e.color }} />
                      {e.label}
                    </span>
                    <span className="tabular font-semibold text-slate-800">{n} <span className="font-normal text-slate-400">· {pct}%</span></span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: e.color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Distribución por plan */}
        <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Por plan</h2>
          {planes.length === 0 ? (
            <p className="mt-4 text-sm text-slate-400">Sin datos.</p>
          ) : (
            <div className="mt-4 space-y-3">
              {planes.map(([plan, n]) => (
                <div key={plan}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-slate-600">{plan}</span>
                    <span className="tabular font-semibold text-slate-800">{n}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-[#2563EB]" style={{ width: `${Math.round((n / maxPlan) * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Trials por vencer */}
      <div className="mt-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Trials por vencer</h2>
          <span className="text-xs text-slate-400">próximos 14 días</span>
        </div>
        {m.trialsPorVencer.length === 0 ? (
          <p className="mt-4 text-sm text-slate-400">No hay trials próximos a vencer.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-50">
            {m.trialsPorVencer.map(({ t, dias }) => (
              <li key={t.id} className="flex items-center justify-between py-2.5">
                <Link to={`/tenants/${t.id}`} className="text-sm font-medium text-slate-700 hover:text-blue-600 hover:underline">
                  {t.nombre} <span className="font-mono text-xs text-slate-400">· {t.schema_name}</span>
                </Link>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${dias < 0 ? "bg-red-100 text-red-700" : dias <= 3 ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600"}`}>
                  {dias < 0 ? `vencido hace ${-dias} d` : dias === 0 ? "vence hoy" : `${dias} d`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Kpi({ label, valor, tono, nota }: { label: string; valor: number; tono: string; nota?: string }) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <p className={`mt-1 text-3xl font-bold tabular ${tono}`}>{valor}</p>
      {nota && <p className="mt-0.5 text-[11px] text-slate-400">{nota}</p>}
    </div>
  );
}
