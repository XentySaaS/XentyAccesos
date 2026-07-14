import { useEffect, useState } from "react";
import api from "../api/client";

interface Entrada {
  id: number;
  evento: string;
  evento_label: string;
  contexto: string;
  contexto_label: string;
  usuario: number | null;
  actor_email: string;
  actor_nombre: string;
  ip: string | null;
  dispositivo: string;
  exito: boolean;
  detalle: string;
  creado: string;
}

const INK = "#0F1B2D";

const EVENTO_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  login:         { bg: "bg-green-100", text: "text-green-800", label: "Inicio de sesión" },
  login_fallido: { bg: "bg-red-100",   text: "text-red-700",   label: "Intento fallido"  },
  logout:        { bg: "bg-slate-100", text: "text-slate-600", label: "Cierre de sesión" },
};

const CONTEXTO_LABEL: Record<string, string> = {
  acceso:      "Operación",
  proveedores: "Proveedores",
};

function fmt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" })
    + " " + d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

export default function AccesosSistema() {
  const [entradas, setEntradas] = useState<Entrada[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [busqueda, setBusqueda] = useState("");
  const [filtroEvento,   setFiltroEvento]   = useState("");
  const [filtroContexto, setFiltroContexto] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (filtroEvento)   params.set("evento", filtroEvento);
    if (filtroContexto) params.set("contexto", filtroContexto);
    if (desde) params.set("fecha_desde", desde);
    if (hasta) params.set("fecha_hasta", hasta);
    setLoading(true);
    api.get(`/api/accesos-sistema/?${params}`)
      .then(r => setEntradas(r.data.results ?? r.data))
      .finally(() => setLoading(false));
  }, [filtroEvento, filtroContexto, desde, hasta]);

  const visibles = busqueda
    ? entradas.filter(e => {
        const q = busqueda.toLowerCase();
        return (e.actor_email ?? "").toLowerCase().includes(q)
          || (e.actor_nombre ?? "").toLowerCase().includes(q)
          || (e.ip ?? "").toLowerCase().includes(q);
      })
    : entradas;

  const hayFiltros = !!(filtroEvento || filtroContexto || desde || hasta || busqueda);

  return (
    <div>
      {/* Encabezado */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ color: INK }}>Accesos al sistema</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Registro de inicios y cierres de sesión e intentos fallidos, con IP y dispositivo. Cubre la
            operación y el panel de proveedores.
          </p>
        </div>
      </div>

      {/* Filtros */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="h-9 w-64 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          placeholder="Buscar por usuario, correo o IP…"
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
        />
        <select
          className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-600 outline-none focus:border-blue-400"
          value={filtroEvento}
          onChange={e => setFiltroEvento(e.target.value)}
        >
          <option value="">Todos los eventos</option>
          <option value="login">Inicio de sesión</option>
          <option value="login_fallido">Intento fallido</option>
          <option value="logout">Cierre de sesión</option>
        </select>
        <select
          className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-600 outline-none focus:border-blue-400"
          value={filtroContexto}
          onChange={e => setFiltroContexto(e.target.value)}
        >
          <option value="">Todos los contextos</option>
          <option value="acceso">Operación</option>
          <option value="proveedores">Proveedores</option>
        </select>
        <input
          type="date"
          className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-600 outline-none focus:border-blue-400"
          value={desde}
          onChange={e => setDesde(e.target.value)}
          title="Desde"
        />
        <input
          type="date"
          className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-600 outline-none focus:border-blue-400"
          value={hasta}
          onChange={e => setHasta(e.target.value)}
          title="Hasta"
        />
        {hayFiltros && (
          <button
            onClick={() => { setFiltroEvento(""); setFiltroContexto(""); setDesde(""); setHasta(""); setBusqueda(""); }}
            className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-500 hover:text-slate-800"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Tabla */}
      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          </div>
        ) : visibles.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-400">
            Sin registros de acceso{hayFiltros ? " para los filtros seleccionados" : ""}.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Fecha</th>
                <th className="px-5 py-3">Usuario</th>
                <th className="px-5 py-3">Evento</th>
                <th className="px-5 py-3">Contexto</th>
                <th className="px-5 py-3">IP</th>
                <th className="px-5 py-3">Dispositivo</th>
                <th className="px-5 py-3">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map(e => {
                const badge = EVENTO_BADGE[e.evento]
                  ?? { bg: "bg-slate-100", text: "text-slate-700", label: e.evento_label };
                return (
                  <tr key={e.id} className="border-b border-slate-50">
                    <td className="px-5 py-3 text-slate-500 whitespace-nowrap">{fmt(e.creado)}</td>
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-700">{e.actor_nombre || "—"}</div>
                      <div className="text-xs text-slate-400">{e.actor_email}</div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.bg} ${badge.text}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-500">{CONTEXTO_LABEL[e.contexto] ?? e.contexto_label}</td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-500">{e.ip ?? "—"}</td>
                    <td className="px-5 py-3 text-slate-500">{e.dispositivo || "—"}</td>
                    <td className="px-5 py-3 text-slate-500 max-w-xs">{e.detalle || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      <p className="mt-2 text-right text-xs text-slate-400">{visibles.length} registro{visibles.length !== 1 ? "s" : ""}</p>
    </div>
  );
}
