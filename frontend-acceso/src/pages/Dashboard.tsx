import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import api from "../api/client";

interface Me    { nombre?: string; email?: string; rol?: string; }
interface HoraItem { hora: string; total: number; }
interface EventoActual {
  id: number; nombre: string; total_invitados: number; total_ingresados: number; porcentaje: number;
}
interface Kpis {
  eventos_vigentes: number; invitados: number; ingresados: number; pendientes_por_ingresar: number;
  accesos_por_hora?: HoraItem[]; eventos_actuales?: EventoActual[];
}

const COLORES_BARRA = ["#DBEAFE","#BFDBFE","#93C5FD","#60A5FA","#3B82F6","#2563EB"];

function colorBarra(index: number, total: number) {
  return COLORES_BARRA[Math.floor((index / Math.max(total, 1)) * COLORES_BARRA.length)] ?? "#2563EB";
}

interface Prov69b { id: number; nombre: string; rfc: string | null; situacion: string | null; }
interface Resumen69b {
  padron_cargado: boolean; importando?: boolean; total_efos?: number;
  marcados: number; proveedores: Prov69b[];
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [me, setMe]    = useState<Me | null>(null);
  const [kpis, setKpis]= useState<Kpis | null>(null);
  const [cumpl, setCumpl] = useState<Resumen69b | null>(null);

  useEffect(() => {
    api.get<Me>("/api/auth/me/").then((r) => setMe(r.data)).catch(() => {});
    api.get<Kpis>("/api/reportes/dashboard/").then((r) => setKpis(r.data)).catch(() => {});
    // Cumplimiento 69-B (solo admin; para otros roles el endpoint responde 403 y se ignora).
    api.get<Resumen69b>("/api/cumplimiento/resumen/")
      .then((r) => setCumpl(r.data)).catch(() => {});
  }, []);

  const horas = kpis?.accesos_por_hora ?? [];
  const sinAccesos = horas.every((h) => h.total === 0);
  const eventos = kpis?.eventos_actuales ?? [];

  const hora = new Date().getHours();
  const saludo = hora < 13 ? "Buenos días" : hora < 19 ? "Buenas tardes" : "Buenas noches";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-extrabold tracking-tight text-ink-900">
            {saludo}{me?.nombre ? `, ${me.nombre.split(" ")[0]}` : ""}.
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {kpis?.eventos_vigentes
              ? `Tienes ${kpis.eventos_vigentes} evento${kpis.eventos_vigentes > 1 ? "s" : ""} en curso hoy.`
              : "Sin eventos activos en este momento."}
          </p>
        </div>
        <button
          className="rounded-lg px-4 py-2 text-sm font-semibold text-white"
          style={{ backgroundColor: "#2563EB" }}
          onClick={() => window.location.href = "/eventos"}
        >
          + Crear evento
        </button>
      </div>

      {/* Cumplimiento SAT 69-B — dato importante de primera instancia */}
      {cumpl && cumpl.marcados > 0 && (
        <div className="overflow-hidden rounded-card border border-red-200 bg-white shadow-card">
          <button onClick={() => navigate("/cumplimiento")}
            className="flex w-full items-center gap-3 border-b border-red-100 bg-[#FEF2F2] px-4 py-3 text-left hover:bg-red-50">
            <svg className="h-5 w-5 flex-shrink-0 text-red-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span className="flex-1 text-sm font-bold text-red-700">
              {cumpl.marcados} proveedor{cumpl.marcados !== 1 ? "es" : ""} en la lista 69-B del SAT
            </span>
            <span className="text-xs font-medium text-red-600">Ver cumplimiento →</span>
          </button>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-4 py-2">Proveedor</th>
                <th className="px-4 py-2">RFC</th>
                <th className="px-4 py-2">Situación SAT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {cumpl.proveedores.slice(0, 5).map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-semibold text-ink-900">{p.nombre}</td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-600">{p.rfc ?? "—"}</td>
                  <td className="px-4 py-2">
                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-700">{p.situacion ?? "—"}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {cumpl.proveedores.length > 5 && (
            <div className="px-4 py-2 text-xs text-slate-400">
              y {cumpl.proveedores.length - 5} más — ver en Cumplimiento.
            </div>
          )}
        </div>
      )}

      {/* Cumplimiento 69-B — estado limpio / actualizándose (visible para admin) */}
      {cumpl && cumpl.marcados === 0 && (
        <button onClick={() => navigate("/cumplimiento")}
          className={`flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left transition ${
            cumpl.padron_cargado ? "border-green-200 bg-[#F0FDF4] hover:bg-green-50" : "border-blue-200 bg-blue-50 hover:bg-blue-100/60"
          }`}>
          {cumpl.padron_cargado ? (
            <>
              <svg className="h-5 w-5 flex-shrink-0 text-green-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/></svg>
              <span className="flex-1 text-sm font-semibold text-green-700">
                Ningún proveedor en la lista 69-B del SAT
                {cumpl.total_efos ? ` · padrón: ${cumpl.total_efos.toLocaleString("es-MX")} RFCs` : ""}
              </span>
            </>
          ) : (
            <>
              <svg className="h-5 w-5 flex-shrink-0 animate-spin text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
              <span className="flex-1 text-sm font-semibold text-blue-700">Actualizando el padrón 69-B del SAT…</span>
            </>
          )}
          <span className="text-xs font-medium text-slate-500">Cumplimiento →</span>
        </button>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard
          label="Invitados hoy"
          value={kpis?.invitados}
          color="text-ink-900"
        />
        <KpiCard
          label="Ingresados"
          value={kpis?.ingresados}
          color="text-[#16A34A]"
          bg="bg-[#F0FDF4]"
          dot="bg-[#16A34A]"
        />
        <KpiCard
          label="Eventos en curso"
          value={kpis?.eventos_vigentes}
          color="text-[#2563EB]"
          bg="bg-[#EFF6FF]"
          dot="bg-[#2563EB]"
        />
        <KpiCard
          label="Por ingresar"
          value={kpis?.pendientes_por_ingresar}
          color="text-[#DC2626]"
          bg="bg-[#FEF2F2]"
          dot="bg-[#DC2626]"
        />
      </div>

      {/* Gráfica + alertas */}
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        {/* Gráfica accesos por hora (entradas de hoy, datos reales) */}
        <div className="rounded-card bg-white p-5 shadow-card">
          <p className="mb-4 text-[13px] font-semibold uppercase tracking-widest text-slate-400">
            Accesos por hora · hoy
          </p>
          {sinAccesos ? (
            <div className="flex h-[220px] items-center justify-center text-sm text-slate-400">
              Aún no hay accesos registrados hoy.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={horas} barSize={18} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F4F8" vertical={false} />
                <XAxis dataKey="hora" tick={{ fontSize: 11, fill: "#94A3B8", fontFamily: "Hanken Grotesk" }} axisLine={false} tickLine={false}
                  tickFormatter={(h) => `${h}h`} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#94A3B8", fontFamily: "Hanken Grotesk" }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(15,27,45,.12)" }}
                  formatter={(v: number) => [v, "accesos"]}
                  labelFormatter={(h) => `${h}:00 h`}
                />
                <Bar dataKey="total" radius={[4,4,0,0]} fill="#2563EB">
                  {horas.map((_, i) => (
                    <Cell key={i} fill={colorBarra(i, horas.length)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Panel derecho: eventos en curso con avance de ingreso (widget del origen) */}
        <div className="rounded-card bg-white p-5 shadow-card space-y-4">
          <p className="text-[13px] font-semibold uppercase tracking-widest text-slate-400">
            Eventos en curso
          </p>
          {eventos.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">
              Sin eventos activos en este momento.
            </div>
          ) : (
            <div className="space-y-3">
              {eventos.map((ev) => (
                <div key={ev.id}>
                  <div className="mb-1 flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm font-semibold text-ink-900">{ev.nombre}</span>
                    <span className="tabular flex-shrink-0 text-xs text-slate-500">
                      {ev.total_ingresados}/{ev.total_invitados}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full transition-all"
                        style={{ width: `${ev.porcentaje}%`, backgroundColor: "#16A34A" }} />
                    </div>
                    <span className="tabular w-9 flex-shrink-0 text-right text-xs font-semibold text-slate-500">
                      {ev.porcentaje}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label, value, color = "text-ink-900", bg = "bg-white", dot,
}: {
  label: string; value?: number; color?: string; bg?: string; dot?: string;
}) {
  return (
    <div className={`${bg} rounded-card shadow-card p-5`}>
      {dot && (
        <span className={`mb-2 inline-block h-2 w-2 rounded-full ${dot}`} />
      )}
      <p className="text-[12px] font-semibold uppercase tracking-widest text-slate-400">{label}</p>
      <p className={`mt-1 text-[30px] font-extrabold tabular leading-none ${color}`}>
        {value !== undefined ? value.toLocaleString("es-MX") : <Skeleton />}
      </p>
    </div>
  );
}

function Skeleton() {
  return <span className="inline-block h-8 w-16 animate-pulse rounded bg-slate-200" />;
}
