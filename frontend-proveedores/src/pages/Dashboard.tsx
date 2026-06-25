import { useEffect, useState } from "react";
import api from "../api/client";

interface Stats {
  total_empleados: number;
  empleados_activos: number;
  documentos_pendientes: number;
  eventos_asignados: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    Promise.all([
      api.get("/api/empleados/empleados/"),
      api.get("/api/documentos/documentos-empleado/?estado=0"),
      api.get("/api/eventos/eventos-proveedor/"),
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
    { label: "Total empleados", value: stats.total_empleados, color: "bg-blue-50 text-blue-700" },
    { label: "Empleados activos", value: stats.empleados_activos, color: "bg-green-50 text-green-700" },
    { label: "Documentos por verificar", value: stats.documentos_pendientes, color: "bg-yellow-50 text-yellow-700" },
    { label: "Eventos asignados", value: stats.eventos_asignados, color: "bg-purple-50 text-purple-700" },
  ] : [];

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Panel del proveedor</h1>
      {stats === null ? (
        <p className="text-slate-500">Cargando…</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c) => (
            <div key={c.label} className={`rounded-xl p-5 ${c.color} shadow-sm`}>
              <p className="text-3xl font-bold">{c.value}</p>
              <p className="mt-1 text-sm">{c.label}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
