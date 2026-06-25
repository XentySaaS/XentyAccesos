import { useEffect, useState } from "react";
import api from "../api/client";

interface EventoProveedor {
  id: number;
  evento: number;
  limite: number;
  requiere_parking: boolean;
  cajones_parking: number;
  notas: string | null;
}

interface Evento {
  id: number;
  nombre: string;
  estado: string;
  vigencia_inicio: string;
  vigencia_fin: string;
  recinto: number;
}

const ESTADO_COLOR: Record<string, string> = {
  programado: "bg-blue-100 text-blue-800",
  en_curso: "bg-green-100 text-green-800",
  completado: "bg-slate-100 text-slate-600",
  cancelado: "bg-red-100 text-red-800",
};

const ESTADO_LABEL: Record<string, string> = {
  programado: "Programado", en_curso: "En curso",
  completado: "Completado", cancelado: "Cancelado",
};

export default function MisEventos() {
  const [asignaciones, setAsignaciones] = useState<EventoProveedor[]>([]);
  const [eventos, setEventos] = useState<Record<number, Evento>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/eventos/eventos-proveedor/").then(async (r) => {
      const lista: EventoProveedor[] = r.data.results ?? r.data;
      setAsignaciones(lista);
      const ids = [...new Set(lista.map((a) => a.evento))];
      if (ids.length) {
        const res = await api.get("/api/eventos/eventos/", { params: { id__in: ids.join(",") } });
        const map: Record<number, Evento> = {};
        (res.data.results ?? res.data).forEach((e: Evento) => { map[e.id] = e; });
        setEventos(map);
      }
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-slate-900">Mis eventos asignados</h1>

      {loading ? (
        <p className="text-slate-500">Cargando…</p>
      ) : asignaciones.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center text-slate-400 shadow-sm">
          <p>No tienes eventos asignados actualmente.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {asignaciones.map((a) => {
            const ev = eventos[a.evento];
            return (
              <div key={a.id} className="rounded-xl border bg-white p-5 shadow-sm">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h2 className="font-semibold text-slate-900">{ev?.nombre ?? `Evento #${a.evento}`}</h2>
                  {ev && (
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_COLOR[ev.estado] ?? "bg-slate-100"}`}>
                      {ESTADO_LABEL[ev.estado] ?? ev.estado}
                    </span>
                  )}
                </div>
                {ev && (
                  <p className="mb-3 text-xs text-slate-500">
                    {ev.vigencia_inicio} → {ev.vigencia_fin}
                  </p>
                )}
                <div className="space-y-1 text-sm text-slate-600">
                  <p>Límite de empleados: <span className="font-medium">{a.limite || "Sin límite"}</span></p>
                  {a.requiere_parking && (
                    <p>Cajones de parking: <span className="font-medium">{a.cajones_parking}</span></p>
                  )}
                  {a.notas && <p className="text-xs italic text-slate-400">{a.notas}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
