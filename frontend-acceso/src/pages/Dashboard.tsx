import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import api from "../api/client";

interface Me    { nombre?: string; email?: string; rol?: string; }
interface Kpis  { eventos_vigentes: number; invitados: number; ingresados: number; pendientes_por_ingresar: number; }
interface HoraItem { hora: string; total: number; }

/* Datos mock para la gráfica mientras el endpoint de reportes se implementa */
const HORAS_MOCK: HoraItem[] = [
  { hora: "07", total: 42 }, { hora: "08", total: 118 }, { hora: "09", total: 195 },
  { hora: "10", total: 230 }, { hora: "11", total: 178 }, { hora: "12", total: 143 },
  { hora: "13", total: 89 }, { hora: "14", total: 67 }, { hora: "15", total: 102 },
  { hora: "16", total: 145 }, { hora: "17", total: 189 }, { hora: "18", total: 74 },
];

const COLORES_BARRA = ["#DBEAFE","#BFDBFE","#93C5FD","#60A5FA","#3B82F6","#2563EB"];

function colorBarra(index: number) {
  return COLORES_BARRA[Math.floor((index / HORAS_MOCK.length) * COLORES_BARRA.length)] ?? "#2563EB";
}

export default function Dashboard() {
  const [me, setMe]    = useState<Me | null>(null);
  const [kpis, setKpis]= useState<Kpis | null>(null);

  useEffect(() => {
    api.get<Me>("/api/auth/me/").then((r) => setMe(r.data)).catch(() => {});
    api.get<Kpis>("/api/reportes/dashboard/").then((r) => setKpis(r.data)).catch(() => {});
  }, []);

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
        {/* Gráfica accesos por hora */}
        <div className="rounded-card bg-white p-5 shadow-card">
          <p className="mb-4 text-[13px] font-semibold uppercase tracking-widest text-slate-400">
            Accesos por hora
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={HORAS_MOCK} barSize={22} margin={{ top: 0, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F4F8" vertical={false} />
              <XAxis dataKey="hora" tick={{ fontSize: 11, fill: "#94A3B8", fontFamily: "Hanken Grotesk" }} axisLine={false} tickLine={false}
                tickFormatter={(h) => `${h}h`} />
              <YAxis tick={{ fontSize: 11, fill: "#94A3B8", fontFamily: "Hanken Grotesk" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(15,27,45,.12)" }}
                formatter={(v: number) => [v, "accesos"]}
                labelFormatter={(h) => `${h}:00 h`}
              />
              <Bar dataKey="total" radius={[4,4,0,0]} fill="#2563EB">
                {HORAS_MOCK.map((_, i) => (
                  <Cell key={i} fill={colorBarra(i)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Panel derecho: alertas */}
        <div className="rounded-card bg-white p-5 shadow-card space-y-4">
          <p className="text-[13px] font-semibold uppercase tracking-widest text-slate-400">
            Avisos del sistema
          </p>
          <Alerta tipo="advertencia" texto="2 documentos por vencer en los próximos 3 días." />
          <Alerta tipo="info"       texto="Dispositivo 'Torniquete Norte' sin respuesta hace 12 min." />
          <div className="rounded-lg border border-dashed border-slate-200 px-4 py-6 text-center text-sm text-slate-400">
            Sin más avisos por ahora.
          </div>
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

function Alerta({ tipo, texto }: { tipo: "advertencia" | "info"; texto: string }) {
  const styles = {
    advertencia: { bg: "bg-[#FFFBEB]", border: "border-[#FCD34D]", dot: "bg-[#D97706]", text: "text-[#92400E]" },
    info:        { bg: "bg-[#EFF6FF]", border: "border-[#BFDBFE]", dot: "bg-[#2563EB]", text: "text-[#1E40AF]" },
  }[tipo];
  return (
    <div className={`${styles.bg} ${styles.border} flex items-start gap-2 rounded-lg border px-3 py-2.5`}>
      <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${styles.dot}`} />
      <p className={`text-xs ${styles.text}`}>{texto}</p>
    </div>
  );
}

function Skeleton() {
  return <span className="inline-block h-8 w-16 animate-pulse rounded bg-slate-200" />;
}
