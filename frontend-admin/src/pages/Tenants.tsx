import { useEffect, useState } from "react";
import api from "../api/client";

interface Tenant {
  id: number;
  schema_name: string;
  nombre: string;
  estado: string;
  plan: string | null;
  saldo: number;
  modo_solo_lectura: boolean;
}

interface Pagina {
  results?: Tenant[];
}

const INK = "#0F1B2D";

const ESTADO_BADGE: Record<string, { bg: string; text: string; label: string; dot: string }> = {
  trial:      { bg: "bg-blue-100",    text: "text-blue-700",    label: "Trial",      dot: "#2563EB" },
  activo:     { bg: "bg-green-100",   text: "text-green-800",   label: "Activo",     dot: "#16A34A" },
  suspendido: { bg: "bg-amber-100",   text: "text-amber-700",   label: "Suspendido", dot: "#D97706" },
  cancelado:  { bg: "bg-red-100",     text: "text-red-700",     label: "Cancelado",  dot: "#DC2626" },
};

export default function Tenants() {
  const [items, setItems]   = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);

  async function cargar() {
    setLoading(true);
    const { data } = await api.get<Pagina | Tenant[]>("/api/admin/tenants/");
    setItems(Array.isArray(data) ? data : data.results ?? []);
    setLoading(false);
  }

  useEffect(() => { cargar().catch(() => setLoading(false)); }, []);

  async function accion(t: Tenant, nombre: "suspender" | "activar" | "cancelar") {
    await api.post(`/api/admin/tenants/${t.id}/${nombre}/`);
    await cargar();
  }

  const conteos = items.reduce<Record<string, number>>((acc, t) => {
    acc[t.estado] = (acc[t.estado] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      {/* Encabezado */}
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Tenants</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Empresas dadas de alta en la suite · estado de suscripción y consumo.
        </p>
      </div>

      {/* Resumen por estado */}
      <div className="mb-4 flex flex-wrap gap-2">
        {Object.entries(ESTADO_BADGE).map(([estado, b]) => (
          <span key={estado} className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 shadow-card ring-1 ring-slate-100">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: b.dot }} />
            {b.label}
            <span className="tabular font-semibold text-slate-900">{conteos[estado] ?? 0}</span>
          </span>
        ))}
      </div>

      {/* Tabla */}
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          </div>
        ) : items.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-400">
            Aún no hay tenants. Las altas llegan desde la landing pública.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Empresa</th>
                <th className="px-5 py-3">Subdominio</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3">Plan</th>
                <th className="px-5 py-3">Créditos</th>
                <th className="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((t) => {
                const b = ESTADO_BADGE[t.estado] ?? { bg: "bg-slate-100", text: "text-slate-700", label: t.estado, dot: "#64748B" };
                return (
                  <tr key={t.id} className="border-b border-slate-50 transition-colors hover:bg-slate-50/60">
                    <td className="px-5 py-3 font-medium text-slate-800">
                      {t.nombre}
                      {t.modo_solo_lectura && (
                        <span className="ml-2 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">solo lectura</span>
                      )}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-500">{t.schema_name}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ${b.bg} ${b.text}`}>
                        <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: b.dot }} />
                        {b.label}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-600">{t.plan ?? "—"}</td>
                    <td className="px-5 py-3 tabular text-slate-700">{t.saldo}</td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-1.5">
                        {t.estado !== "suspendido" && (
                          <button onClick={() => accion(t, "suspender")}
                            className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">
                            Suspender
                          </button>
                        )}
                        {t.estado !== "activo" && (
                          <button onClick={() => accion(t, "activar")}
                            className="rounded-lg bg-[#16A34A] px-2.5 py-1 text-xs font-medium text-white hover:opacity-90">
                            Activar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      <p className="mt-2 text-right text-xs text-slate-400">{items.length} tenant{items.length !== 1 ? "s" : ""}</p>
    </div>
  );
}
