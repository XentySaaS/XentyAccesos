import { useEffect, useState } from "react";
import api from "../api/client";

interface Documento {
  id: number;
  empleado: number;
  tipo_documento: number;
  archivo: string;
  tipo_archivo: string | null;
  estado: number;
  motivo_rechazo: string | null;
  creado: string;
}

interface Empleado { id: number; nombre: string; }
interface TipoDocumento { id: number; nombre: string; }

const ESTADO_LABEL = ["Pendiente", "Verificado", "Rechazado"];
const ESTADO_COLOR = [
  "bg-yellow-100 text-yellow-800",
  "bg-green-100 text-green-800",
  "bg-red-100 text-red-800",
];

export default function Verificacion() {
  const [docs, setDocs] = useState<Documento[]>([]);
  const [empleados, setEmpleados] = useState<Empleado[]>([]);
  const [tipos, setTipos] = useState<TipoDocumento[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState("0"); // Pendiente por defecto
  const [rechazoId, setRechazoId] = useState<number | null>(null);
  const [motivo, setMotivo] = useState("");
  const [procesando, setProcesando] = useState<number | null>(null);

  const cargar = () => {
    const params: Record<string, string> = {};
    if (filtroEstado !== "") params.estado = filtroEstado;
    Promise.all([
      api.get("/api/documentos/documentos-empleado/", { params }),
      api.get("/api/empleados/empleados/"),
      api.get("/api/documentos/tipos-documento/"),
    ]).then(([d, e, t]) => {
      setDocs(d.data.results ?? d.data);
      setEmpleados(e.data.results ?? e.data);
      setTipos(t.data.results ?? t.data);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [filtroEstado]);

  const aprobar = async (id: number) => {
    setProcesando(id);
    try { await api.post(`/api/documentos/documentos-empleado/${id}/aprobar/`); cargar(); }
    finally { setProcesando(null); }
  };

  const rechazar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rechazoId) return;
    setProcesando(rechazoId);
    try {
      await api.post(`/api/documentos/documentos-empleado/${rechazoId}/rechazar/`, { motivo });
      setRechazoId(null); setMotivo(""); cargar();
    } finally { setProcesando(null); }
  };

  const nombreEmpleado = (id: number) => empleados.find((e) => e.id === id)?.nombre ?? `#${id}`;
  const nombreTipo = (id: number) => tipos.find((t) => t.id === id)?.nombre ?? `#${id}`;

  const pendientes = docs.filter((d) => d.estado === 0).length;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">
          Verificación de documentos
          {pendientes > 0 && (
            <span className="ml-2 rounded-full bg-yellow-500 px-2 py-0.5 text-sm text-white">{pendientes}</span>
          )}
        </h1>
        <div className="ml-auto">
          <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}
            className="rounded border px-2 py-1 text-sm">
            <option value="">Todos</option>
            <option value="0">Pendientes</option>
            <option value="1">Verificados</option>
            <option value="2">Rechazados</option>
          </select>
        </div>
      </div>

      {/* Modal rechazo */}
      {rechazoId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <form onSubmit={rechazar} className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-3 text-lg font-semibold">Rechazar documento</h2>
            <label className="mb-1 block text-xs font-medium text-slate-600">Motivo del rechazo</label>
            <textarea required rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm"
              placeholder="Documento ilegible, información incorrecta…" />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => { setRechazoId(null); setMotivo(""); }}
                className="rounded border px-4 py-1 text-sm">Cancelar</button>
              <button type="submit" disabled={procesando !== null}
                className="rounded bg-red-600 px-4 py-1 text-sm text-white disabled:opacity-50">
                Rechazar
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <p className="text-slate-500">Cargando…</p>
      ) : docs.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center text-slate-400 shadow-sm">
          <p>No hay documentos en esta bandeja.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b bg-slate-50 text-xs text-slate-500">
              <tr>
                {["Empleado", "Tipo de documento", "Archivo", "Estado", "Motivo rechazo", "Fecha", "Acciones"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-b hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{nombreEmpleado(d.empleado)}</td>
                  <td className="px-4 py-2 text-slate-600">{nombreTipo(d.tipo_documento)}</td>
                  <td className="px-4 py-2">
                    {d.archivo ? (
                      <a href={d.archivo} target="_blank" rel="noreferrer"
                        className="text-blue-600 underline hover:text-blue-800">
                        Ver {d.tipo_archivo?.toUpperCase() ?? "archivo"}
                      </a>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ESTADO_COLOR[d.estado] ?? "bg-slate-100"}`}>
                      {ESTADO_LABEL[d.estado] ?? d.estado}
                    </span>
                  </td>
                  <td className="max-w-xs px-4 py-2 text-xs text-red-600">{d.motivo_rechazo ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-500 whitespace-nowrap">
                    {new Date(d.creado).toLocaleDateString("es-MX")}
                  </td>
                  <td className="flex gap-1 px-4 py-2">
                    {d.estado === 0 && (
                      <>
                        <button
                          onClick={() => aprobar(d.id)}
                          disabled={procesando === d.id}
                          className="rounded bg-green-600 px-2 py-0.5 text-xs text-white disabled:opacity-50">
                          Aprobar
                        </button>
                        <button
                          onClick={() => { setRechazoId(d.id); setMotivo(""); }}
                          disabled={procesando === d.id}
                          className="rounded bg-red-500 px-2 py-0.5 text-xs text-white disabled:opacity-50">
                          Rechazar
                        </button>
                      </>
                    )}
                    {d.estado === 2 && (
                      <button
                        onClick={() => aprobar(d.id)}
                        disabled={procesando === d.id}
                        className="rounded border px-2 py-0.5 text-xs hover:bg-slate-50 disabled:opacity-50">
                        Re-aprobar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
