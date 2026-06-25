import { useEffect, useState } from "react";
import api from "../api/client";

interface Me {
  email?: string;
  nombre?: string;
  rol?: string;
}
interface Kpis {
  eventos_vigentes: number;
  invitados: number;
  ingresados: number;
  pendientes_por_ingresar: number;
}

export default function Dashboard() {
  const [me, setMe] = useState<Me | null>(null);
  const [kpis, setKpis] = useState<Kpis | null>(null);

  useEffect(() => {
    api.get<Me>("/api/auth/me/").then((r) => setMe(r.data)).catch(() => {});
    // KPIs solo para administrador; si no, se omite silenciosamente.
    api.get<Kpis>("/api/reportes/dashboard/").then((r) => setKpis(r.data)).catch(() => {});
  }, []);

  const tarjetas: [string, number | undefined][] = [
    ["Eventos vigentes", kpis?.eventos_vigentes],
    ["Invitados", kpis?.invitados],
    ["Ingresados", kpis?.ingresados],
    ["Por ingresar", kpis?.pendientes_por_ingresar],
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-semibold">Panel</h1>

      {kpis && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {tarjetas.map(([t, v]) => (
            <div key={t} className="rounded-lg bg-white p-5 shadow">
              <p className="text-sm text-slate-500">{t}</p>
              <p className="mt-1 text-3xl font-bold">{v ?? 0}</p>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-lg bg-white p-6 shadow">
        <p className="text-slate-600">Sesión iniciada como:</p>
        <p className="text-lg font-medium">{me?.nombre ?? "…"}</p>
        <p className="text-sm text-slate-500">{me?.email}</p>
        {me?.rol && <p className="mt-1 text-sm">Rol: {me.rol}</p>}
      </div>
    </div>
  );
}
