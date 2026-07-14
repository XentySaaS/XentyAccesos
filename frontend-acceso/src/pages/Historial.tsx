import { useEffect, useState } from "react";
import api from "../api/client";

interface Entrada {
  id: number;
  descripcion: string;
  modelo: string | null;
  modelo_id: number | null;
  usuario: number | null;
  usuario_nombre: string;
  accion: string;
  creado: string;
  antes: Record<string, unknown> | null;
  despues: Record<string, unknown> | null;
}

const INK = "#0F1B2D";

const ACCION_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  creado:      { bg: "bg-green-100",  text: "text-green-800",  label: "Creado"      },
  actualizado: { bg: "bg-blue-100",   text: "text-blue-800",   label: "Actualizado" },
  eliminado:   { bg: "bg-red-100",    text: "text-red-700",    label: "Eliminado"   },
  restaurado:  { bg: "bg-purple-100", text: "text-purple-800", label: "Restaurado"  },
  asignado:    { bg: "bg-cyan-100",   text: "text-cyan-800",   label: "Asignado"    },
  desasignado: { bg: "bg-slate-100",  text: "text-slate-700",  label: "Desasignado" },
  visto:       { bg: "bg-amber-100",  text: "text-amber-700",  label: "Visto"       },
  listado:     { bg: "bg-slate-100",  text: "text-slate-600",  label: "Listado"     },
};

const ACCIONES = Object.keys(ACCION_BADGE);
const MODELOS  = [
  "Recinto","Area","Evento","Cita","Proveedor","Empleado",
  "GrupoDocumentos","TipoDocumento","Protocolo","Sancion",
];

function fmt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" })
    + " " + d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

const SIN_DESCRIPCION = "No se agregó una descripción";

// Etiquetas amigables para los campos que aparecen en el detalle (antes/después).
const CAMPO_LABEL: Record<string, string> = {
  cuerpo: "Cuerpo", segmento: "Segmento", segmento_id: "Segmento", creado_por: "Creado por",
  nombre: "Nombre", descripcion: "Descripción", detalles: "Detalles",
  observaciones: "Observaciones", motivo: "Motivo", motivo_rechazo: "Motivo de rechazo",
  estado: "Estado", email: "Correo", email_responsable: "Correo del responsable",
  telefono: "Teléfono", rfc: "RFC", razon_social: "Razón social", fecha: "Fecha",
  fecha_baja: "Fecha de baja", hora_inicio: "Hora de inicio", hora_fin: "Hora de fin",
  activo: "Activo", tipo: "Tipo", tipo_cita: "Tipo de cita", limite: "Límite de personas",
  recinto: "Recinto", ubicacion: "Ubicación", punto_acceso: "Punto de acceso",
  protocolo: "Protocolo", zona: "Zona", vigencia_inicio: "Vigencia desde",
  vigencia_fin: "Vigencia hasta", nombre_responsable: "Nombre del responsable",
  puesto: "Puesto", requiere_ine: "Requiere INE", requiere_parking: "Requiere estacionamiento",
  cajones_parking: "Cajones de estacionamiento", parking: "Estacionamiento",
};

// Campos donde un valor vacío debe leerse como «No se agregó una descripción».
const CAMPOS_DESCRIPCION = new Set([
  "descripcion", "descripción", "detalles", "observaciones", "motivo",
  "motivo_rechazo", "nota", "notas", "comentario", "comentarios",
]);

function etiquetaCampo(k: string): string {
  if (CAMPO_LABEL[k]) return CAMPO_LABEL[k];
  const base = k.replace(/_id$/, "").replace(/_/g, " ");
  return base.charAt(0).toUpperCase() + base.slice(1);
}

function valorCampo(k: string, v: unknown): string {
  if (v === null || v === undefined || v === "") {
    return CAMPOS_DESCRIPCION.has(k.toLowerCase()) ? SIN_DESCRIPCION : "—";
  }
  if (typeof v === "boolean") return v ? "Sí" : "No";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

/** Detalle amigable: lista «Campo: valor» en vez de JSON crudo. */
function Campos({ datos }: { datos: Record<string, unknown> }) {
  const keys = Object.keys(datos ?? {});
  if (keys.length === 0) return <p className="px-3 py-2 text-xs text-slate-400">Sin datos.</p>;
  return (
    <dl className="divide-y divide-slate-100 overflow-hidden rounded-xl bg-white ring-1 ring-slate-200">
      {keys.map(k => (
        <div key={k} className="flex gap-3 px-3 py-2 text-xs">
          <dt className="w-36 shrink-0 font-medium text-slate-500">{etiquetaCampo(k)}</dt>
          <dd className="flex-1 break-words text-slate-700">{valorCampo(k, datos[k])}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function Historial() {
  const [entradas, setEntradas] = useState<Entrada[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [busqueda, setBusqueda] = useState("");
  const [filtroAccion, setFiltroAccion] = useState("");
  const [filtroModelo, setFiltroModelo] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (filtroAccion) params.set("accion", filtroAccion);
    if (filtroModelo) params.set("modelo", filtroModelo);
    setLoading(true);
    api.get(`/api/historial/?${params}`)
      .then(r => setEntradas(r.data.results ?? r.data))
      .finally(() => setLoading(false));
  }, [filtroAccion, filtroModelo]);

  const visibles = busqueda
    ? entradas.filter(e =>
        e.descripcion.toLowerCase().includes(busqueda.toLowerCase()) ||
        (e.usuario_nombre ?? "").toLowerCase().includes(busqueda.toLowerCase()) ||
        (e.modelo ?? "").toLowerCase().includes(busqueda.toLowerCase())
      )
    : entradas;

  return (
    <div>
      {/* Encabezado */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ color: INK }}>Historial de cambios</h1>
          <p className="mt-0.5 text-sm text-slate-500">Registro de todas las acciones realizadas por usuarios del sistema.</p>
        </div>
      </div>

      {/* Filtros */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="h-9 w-64 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          placeholder="Buscar por descripción, usuario…"
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
        />
        <select
          className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-600 outline-none focus:border-blue-400"
          value={filtroAccion}
          onChange={e => setFiltroAccion(e.target.value)}
        >
          <option value="">Todas las acciones</option>
          {ACCIONES.map(a => (
            <option key={a} value={a}>{ACCION_BADGE[a]?.label ?? a}</option>
          ))}
        </select>
        <select
          className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-600 outline-none focus:border-blue-400"
          value={filtroModelo}
          onChange={e => setFiltroModelo(e.target.value)}
        >
          <option value="">Todos los módulos</option>
          {MODELOS.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        {(filtroAccion || filtroModelo || busqueda) && (
          <button
            onClick={() => { setFiltroAccion(""); setFiltroModelo(""); setBusqueda(""); }}
            className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-500 hover:text-slate-800"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Tabla */}
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          </div>
        ) : visibles.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-400">
            Sin registros de auditoría{busqueda || filtroAccion || filtroModelo ? " para los filtros seleccionados" : ""}.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Fecha</th>
                <th className="px-5 py-3">Usuario</th>
                <th className="px-5 py-3">Acción</th>
                <th className="px-5 py-3">Módulo</th>
                <th className="px-5 py-3">Descripción</th>
                <th className="px-5 py-3 w-10" />
              </tr>
            </thead>
            <tbody>
              {visibles.map(e => {
                const badge = ACCION_BADGE[e.accion] ?? { bg: "bg-slate-100", text: "text-slate-700", label: e.accion };
                const open  = expanded === e.id;
                const hasDiff = e.antes || e.despues;
                return (
                  <>
                    <tr
                      key={e.id}
                      className={`border-b border-slate-50 transition-colors ${hasDiff ? "cursor-pointer hover:bg-slate-50/60" : ""}`}
                      onClick={() => hasDiff && setExpanded(open ? null : e.id)}
                    >
                      <td className="px-5 py-3 text-slate-500 whitespace-nowrap">{fmt(e.creado)}</td>
                      <td className="px-5 py-3 font-medium text-slate-700">{e.usuario_nombre}</td>
                      <td className="px-5 py-3">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.bg} ${badge.text}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-slate-500">{e.modelo ?? "—"}</td>
                      <td className="px-5 py-3 text-slate-700 max-w-sm">{e.descripcion || SIN_DESCRIPCION}</td>
                      <td className="px-3 py-3 text-center">
                        {hasDiff && (
                          <svg
                            className={`mx-auto h-4 w-4 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
                            fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
                          ><path d="M19 9l-7 7-7-7"/></svg>
                        )}
                      </td>
                    </tr>
                    {open && hasDiff && (
                      <tr key={`${e.id}-diff`} className="bg-slate-50">
                        <td colSpan={6} className="px-5 pb-4 pt-2">
                          <div className="grid grid-cols-2 gap-4">
                            {e.antes && (
                              <div>
                                <p className="mb-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">Antes</p>
                                <Campos datos={e.antes} />
                              </div>
                            )}
                            {e.despues && (
                              <div>
                                <p className="mb-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">Después</p>
                                <Campos datos={e.despues} />
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
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
