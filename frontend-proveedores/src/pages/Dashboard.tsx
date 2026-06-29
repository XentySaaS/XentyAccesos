import { useEffect, useState } from "react";
import api from "../api/client";

interface Stats {
  total_empleados: number;
  empleados_activos: number;
  documentos_pendientes: number;
  eventos_asignados: number;
}

const INK = "#0F1B2D";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    Promise.all([
      api.get("/api/empleados/"),
      api.get("/api/documentos-empleado/?estado=0"),
      api.get("/api/evento-proveedores/"),
    ]).then(([emp, docs, evs]) => {
      const todos: { estado: string }[] = emp.data.results ?? emp.data;
      setStats({
        total_empleados: todos.length,
        empleados_activos: todos.filter((e) => e.estado === "activo").length,
        documentos_pendientes: (docs.data.results ?? docs.data).length,
        eventos_asignados: (evs.data.results ?? evs.data).length,
      });
    }).catch(() => {});
  }, []);

  const cards = stats ? [
    { label: "Total empleados",        value: stats.total_empleados,        color: INK },
    { label: "Empleados activos",      value: stats.empleados_activos,      color: "#16A34A" },
    { label: "Documentos por verificar", value: stats.documentos_pendientes, color: "#D97706" },
    { label: "Eventos asignados",      value: stats.eventos_asignados,      color: "#2563EB" },
  ] : [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Panel del proveedor</h1>
        <p className="mt-0.5 text-sm text-slate-500">Resumen de tu plantilla, documentos y eventos.</p>
      </div>

      {stats === null ? (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-card bg-white shadow-card ring-1 ring-slate-100" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c) => (
            <div key={c.label} className="rounded-card bg-white p-5 shadow-card ring-1 ring-slate-100">
              <p className="text-[30px] font-extrabold leading-none tabular" style={{ color: c.color }}>{c.value}</p>
              <p className="mt-2 text-xs font-semibold uppercase tracking-wider text-slate-400">{c.label}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
