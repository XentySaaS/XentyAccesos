/**
 * Bitácora — dossier de solo lectura por evento (recrea la "Bitácora" del sistema origen).
 *
 * Lista de eventos → "Ver detalles" muestra el resumen consolidado: datos del evento y cada
 * proveedor invitado con su configuración (zona, acceso, protocolo, estacionamiento, notas) y su
 * staff (empleados invitados, con modal de detalle). No expone QR ni edición.
 */
import { useCallback, useEffect, useState } from "react";
import api from "../api/client";

/* ── Tipos ──────────────────────────────────────────────────────────────── */
interface EventoLista {
  id: number; nombre: string; recinto: number; estado: string; vigencia_inicio: string;
}
interface Recinto { id: number; nombre: string; }

interface EmpleadoBita {
  id: number; nombre: string; email: string | null; telefono: string | null;
  foto_url: string | null; statusdocs: number | null;
}
interface ProveedorBita {
  id: number; proveedor: string; responsable: string | null; email_responsable: string | null;
  zona: string | null; acceso: string | null; protocolo: string | null;
  requiere_parking: boolean; parking: string | null; cajones_parking: number;
  notas: string | null; empleados: EmpleadoBita[]; total_empleados: number;
}
interface Dossier {
  evento: {
    id: number; nombre: string; recinto: string | null; estado: string;
    vigencia_inicio: string; vigencia_fin: string;
    hora_inicio: string | null; hora_fin: string | null; protocolo: string | null;
  };
  proveedores: ProveedorBita[];
  total_proveedores: number;
}

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const ESTADO_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  programado: { bg: "bg-blue-50",   text: "text-blue-700",  label: "Programado" },
  en_curso:   { bg: "bg-green-50",  text: "text-green-700", label: "En curso"   },
  completado: { bg: "bg-slate-100", text: "text-slate-600", label: "Completado" },
  cancelado:  { bg: "bg-red-50",    text: "text-red-600",   label: "Cancelado"  },
};

function lista<T>(d: { results?: T[] } | T[]): T[] {
  return Array.isArray(d) ? d : (d.results ?? []);
}
function fmt(date: string) {
  if (!date) return "—";
  const [y, m, d] = date.split("-");
  const meses = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  return `${d} ${meses[Number(m) - 1]} ${y}`;
}

function EstadoBadge({ estado }: { estado: string }) {
  const s = ESTADO_STYLE[estado] ?? { bg: "bg-slate-100", text: "text-slate-600", label: estado };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  );
}

/* ══════════════════════════════════════════════════════════════════════════
   Página principal
   ══════════════════════════════════════════════════════════════════════════ */
export default function Bitacora() {
  const [items,    setItems]    = useState<EventoLista[]>([]);
  const [recintos, setRecintos] = useState<Recinto[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error,    setError]    = useState<string | null>(null);

  const [dossier,  setDossier]  = useState<Dossier | null>(null);
  const [cargandoDos, setCargandoDos] = useState(false);
  const [empleadoSel, setEmpleadoSel] = useState<EmpleadoBita | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const [ev, rec] = await Promise.all([
        api.get("/api/eventos/"),
        api.get("/api/recintos/"),
      ]);
      setItems(lista(ev.data));
      setRecintos(lista(rec.data));
    } catch {
      setError("No se pudo cargar la bitácora.");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  async function verDetalle(id: number) {
    setCargandoDos(true);
    setDossier(null);
    try {
      const { data } = await api.get<Dossier>(`/api/eventos/${id}/bitacora/`);
      setDossier(data);
    } catch {
      setError("No se pudo cargar el detalle del evento.");
    } finally {
      setCargandoDos(false);
    }
  }

  /* ── Vista de detalle (dossier) ───────────────────────────────── */
  if (dossier || cargandoDos) {
    return (
      <div className="space-y-5">
        <button onClick={() => setDossier(null)}
          className="flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-700">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
          Volver a la bitácora
        </button>

        {cargandoDos && (
          <div className="rounded-card bg-white p-6 shadow-card">
            <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />)}</div>
          </div>
        )}

        {dossier && (
          <>
            {/* Datos del evento */}
            <div className="rounded-card bg-white p-6 shadow-card">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Bitácora de evento</p>
                  <h1 className="mt-0.5 text-[22px] font-extrabold tracking-tight" style={{ color: INK }}>
                    {dossier.evento.nombre}
                  </h1>
                </div>
                <EstadoBadge estado={dossier.evento.estado} />
              </div>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-3">
                <Dato k="Recinto" v={dossier.evento.recinto ?? "—"} />
                <Dato k="Fecha del evento" v={fmt(dossier.evento.vigencia_inicio)} />
                <Dato k="Protocolo" v={dossier.evento.protocolo ?? "—"} />
                <Dato k="Vigencia desde" v={fmt(dossier.evento.vigencia_inicio)} />
                <Dato k="Vigencia hasta" v={fmt(dossier.evento.vigencia_fin)} />
                <Dato k="Horario" v={dossier.evento.hora_inicio ? `${dossier.evento.hora_inicio.slice(0,5)}${dossier.evento.hora_fin ? " – " + dossier.evento.hora_fin.slice(0,5) : ""}` : "—"} />
              </dl>
            </div>

            {/* Proveedores invitados */}
            <div>
              <h2 className="mb-3 text-base font-bold" style={{ color: INK }}>
                Proveedores invitados
                <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">
                  {dossier.total_proveedores}
                </span>
              </h2>

              {dossier.proveedores.length === 0 && (
                <p className="rounded-card bg-white px-5 py-8 text-center text-sm text-slate-400 shadow-card">
                  Este evento no tiene proveedores invitados.
                </p>
              )}

              <div className="space-y-4">
                {dossier.proveedores.map(p => (
                  <div key={p.id} className="rounded-card bg-white p-5 shadow-card">
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="text-base font-bold" style={{ color: INK }}>{p.proveedor}</p>
                        <p className="text-xs text-slate-400">
                          Responsable: {p.responsable ?? "No asignado"}
                          {p.email_responsable ? ` · ${p.email_responsable}` : ""}
                        </p>
                      </div>
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-500">
                        {p.total_empleados} empleado{p.total_empleados !== 1 ? "s" : ""}
                      </span>
                    </div>

                    <dl className="mb-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-3">
                      <Dato k="Zona" v={p.zona ?? "No asignado"} />
                      <Dato k="Punto de acceso" v={p.acceso ?? "No asignado"} />
                      <Dato k="Protocolo" v={p.protocolo ?? "No asignado"} />
                      <Dato k="Estacionamiento" v={p.requiere_parking ? (p.parking || "Sí") : "No"} />
                      <Dato k="# de cajones" v={p.requiere_parking ? String(p.cajones_parking) : "—"} />
                      <Dato k="Notas adicionales" v={p.notas || "—"} />
                    </dl>

                    {/* Staff / empleados invitados */}
                    <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">
                      Staff · empleados invitados
                    </p>
                    {p.empleados.length === 0 ? (
                      <p className="text-xs text-slate-400">Sin empleados asignados aún.</p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {p.empleados.map(e => (
                          <button key={e.id} onClick={() => setEmpleadoSel(e)}
                            className="flex items-center gap-2 rounded-full border border-slate-200 py-1 pl-1 pr-3 text-sm transition-colors hover:border-slate-300 hover:bg-slate-50">
                            <FotoMini foto={e.foto_url} nombre={e.nombre} />
                            <span className="font-medium text-slate-700">{e.nombre}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Modal detalle del empleado */}
        {empleadoSel && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            onClick={() => setEmpleadoSel(null)}>
            <div className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel" onClick={e => e.stopPropagation()}>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-bold" style={{ color: INK }}>Detalles del empleado</h2>
                <button onClick={() => setEmpleadoSel(null)}
                  className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              </div>
              <div className="flex flex-col items-center gap-3 text-center">
                <FotoGrande foto={empleadoSel.foto_url} nombre={empleadoSel.nombre} />
                <p className="text-lg font-bold" style={{ color: INK }}>{empleadoSel.nombre}</p>
              </div>
              <dl className="mt-4 space-y-2 text-sm">
                <Dato k="Correo electrónico" v={empleadoSel.email ?? "N/A"} />
                <Dato k="Teléfono" v={empleadoSel.telefono ?? "N/A"} />
                <Dato k="Estado documental" v={empleadoSel.statusdocs === 1 ? "Cumple" : "Documentos pendientes"} />
              </dl>
            </div>
          </div>
        )}
      </div>
    );
  }

  /* ── Vista de lista ───────────────────────────────────────────── */
  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Bitácora › Eventos</p>
        <h1 className="mt-0.5 text-[22px] font-extrabold tracking-tight" style={{ color: INK }}>Bitácora</h1>
        <p className="text-xs text-slate-500">Resumen consolidado por evento: proveedores invitados y su staff.</p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button className="ml-3 underline" onClick={() => setError(null)}>Cerrar</button>
        </div>
      )}

      <div className="overflow-hidden rounded-card bg-white shadow-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <th className="px-5 py-3">Fecha del evento</th>
              <th className="px-5 py-3">Nombre del evento</th>
              <th className="px-5 py-3">Recinto</th>
              <th className="px-5 py-3">Estado</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {cargando && (
              <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-400">Cargando…</td></tr>
            )}
            {!cargando && items.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-400">Aún no hay eventos.</td></tr>
            )}
            {items.map(ev => {
              const rec = recintos.find(r => r.id === ev.recinto);
              return (
                <tr key={ev.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="tabular px-5 py-3 text-slate-500">{fmt(ev.vigencia_inicio)}</td>
                  <td className="px-5 py-3 font-medium text-ink-900">{ev.nombre}</td>
                  <td className="px-5 py-3">
                    {rec && (
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">{rec.nombre}</span>
                    )}
                  </td>
                  <td className="px-5 py-3"><EstadoBadge estado={ev.estado} /></td>
                  <td className="px-5 py-3 text-right">
                    <button onClick={() => verDetalle(ev.id)}
                      className="rounded border border-slate-200 px-3 py-1 text-xs font-medium hover:bg-slate-50 transition-colors"
                      style={{ color: SIGNAL }}>
                      Ver detalles
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="border-t border-slate-100 px-5 py-2.5 text-xs text-slate-400">
          Se muestran {items.length} evento{items.length !== 1 ? "s" : ""}
        </div>
      </div>
    </div>
  );
}

/* ── Subcomponentes ───────────────────────────────────────────────── */
function Dato({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{k}</dt>
      <dd className="text-slate-700">{v}</dd>
    </div>
  );
}

function FotoMini({ foto, nombre }: { foto: string | null; nombre: string }) {
  const [err, setErr] = useState(false);
  if (foto && !err) {
    return <img src={foto} alt={nombre} onError={() => setErr(true)}
      className="h-6 w-6 rounded-full object-cover" />;
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold text-white"
      style={{ backgroundColor: SIGNAL }}>
      {nombre[0]?.toUpperCase() ?? "?"}
    </span>
  );
}

function FotoGrande({ foto, nombre }: { foto: string | null; nombre: string }) {
  const [err, setErr] = useState(false);
  if (foto && !err) {
    return <img src={foto} alt={nombre} onError={() => setErr(true)}
      className="h-24 w-24 rounded-full object-cover ring-4 ring-slate-100" />;
  }
  return (
    <span className="flex h-24 w-24 items-center justify-center rounded-full text-3xl font-bold text-white ring-4 ring-slate-100"
      style={{ backgroundColor: SIGNAL }}>
      {nombre[0]?.toUpperCase() ?? "?"}
    </span>
  );
}
