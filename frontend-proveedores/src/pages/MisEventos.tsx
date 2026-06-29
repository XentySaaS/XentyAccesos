import { useEffect, useRef, useState } from "react";
import api from "../api/client";

const INK = "#0F1B2D";

interface Invitacion {
  id: number;
  evento: number;
  evento_nombre: string;
  evento_estado: string;
  evento_descripcion?: string;
  vigencia_inicio: string | null;
  vigencia_fin: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  recinto_nombre: string;
  zona_nombre?: string;
  acceso_nombre?: string;
  protocolo_nombre?: string;
  areas_nombres?: string[];
  limite: number;
  asignados: number;
  requiere_parking: boolean;
  parking?: string | null;
}

interface GrupoDetalle {
  grupo: number;
  grupo_nombre: string;
  type_validation: number;
  ok: boolean;
  verificados: string[];
  pendientes: string[];
  faltantes: string[];
  tipos: { id: number; nombre: string }[];
}
interface Candidato {
  id: number;
  nombre: string;
  asignado: boolean;
  statusdocs: number | null; // 0=docs pendientes, 1=cumple, null=no asignado
  cumple: boolean;
  detalle: GrupoDetalle[];
}
interface CandidatosResp {
  empleados: Candidato[];
  limite: number;
  asignados_count: number;
  requiere_documentos: boolean;
}

const EVENTO_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  programado: { bg: "bg-blue-100",  text: "text-blue-700",  label: "Programado" },
  en_curso:   { bg: "bg-green-100", text: "text-green-800", label: "En curso" },
  completado: { bg: "bg-slate-100", text: "text-slate-600", label: "Completado" },
  cancelado:  { bg: "bg-red-100",   text: "text-red-700",   label: "Cancelado" },
};

function fechaCorta(iso: string | null) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  const meses = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  return `${d} ${meses[Number(m) - 1]} ${y}`;
}

/* Dato etiqueta/valor para el bloque de detalles. */
function Detalle({ label, valor }: { label: string; valor: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-sm text-slate-700">{valor}</p>
    </div>
  );
}

/* Tipos de documento que el empleado aún no ha subido (para el uploader). */
function tiposSubibles(c: Candidato): { id: number; nombre: string }[] {
  const out: { id: number; nombre: string }[] = [];
  c.detalle.forEach(g => {
    if (g.ok) return;
    g.tipos.forEach(t => { if (g.faltantes.includes(t.nombre)) out.push(t); });
  });
  return Array.from(new Map(out.map(t => [t.id, t])).values());
}

export default function MisEventos() {
  const [invitaciones, setInvitaciones] = useState<Invitacion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* gestión de empleados de una invitación */
  const [gestion, setGestion] = useState<Invitacion | null>(null);
  const [cand, setCand] = useState<CandidatosResp | null>(null);
  const [loadingCand, setLoadingCand] = useState(false);
  const [accion, setAccion] = useState<number | null>(null);     // empleado en proceso
  const [aviso, setAviso] = useState("");

  const cargar = () =>
    api.get("/api/evento-proveedores/")
      .then(r => setInvitaciones(r.data.results ?? r.data))
      .catch(() => setError("No se pudieron cargar tus eventos."))
      .finally(() => setLoading(false));

  useEffect(() => { cargar(); }, []);

  async function abrirGestion(inv: Invitacion) {
    setGestion(inv); setCand(null); setAviso(""); setLoadingCand(true);
    try {
      const { data } = await api.get(`/api/evento-proveedores/${inv.id}/candidatos/`);
      setCand(data);
    } catch {
      setError("No se pudieron cargar los empleados.");
      setGestion(null);
    } finally { setLoadingCand(false); }
  }

  async function recargarCand() {
    if (!gestion) return;
    const { data } = await api.get(`/api/evento-proveedores/${gestion.id}/candidatos/`);
    setCand(data);
  }

  async function asignar(emp: Candidato) {
    if (!gestion) return;
    setAccion(emp.id); setAviso("");
    try {
      await api.post(`/api/evento-proveedores/${gestion.id}/asignar-empleados/`, { empleados: [emp.id] });
      await recargarCand();
      await cargar();
    } catch (err: any) {
      setAviso(err?.response?.data?.detail ?? "No se pudo asignar.");
    } finally { setAccion(null); }
  }

  async function quitar(emp: Candidato) {
    if (!gestion) return;
    setAccion(emp.id); setAviso("");
    try {
      await api.post(`/api/evento-proveedores/${gestion.id}/desasignar-empleados/`, { empleados: [emp.id] });
      await recargarCand();
      await cargar();
    } catch {
      setAviso("No se pudo quitar al empleado.");
    } finally { setAccion(null); }
  }

  const cupoLleno = !!cand && cand.limite > 0 && cand.asignados_count >= cand.limite;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Mis eventos asignados</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Asigna a tu personal a cada evento. Si faltan documentos, el empleado queda registrado
          como pendiente — sube los documentos requeridos y el recinto los verificará.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map(i => <div key={i} className="h-40 animate-pulse rounded-card bg-white shadow-card ring-1 ring-slate-100" />)}
        </div>
      ) : invitaciones.length === 0 ? (
        <div className="rounded-2xl bg-white py-16 text-center shadow-sm ring-1 ring-slate-100">
          <p className="text-sm text-slate-500">Aún no tienes eventos asignados.</p>
          <p className="mt-1 text-xs text-slate-400">El recinto te asignará a un evento cuando corresponda.</p>
        </div>
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {invitaciones.map(inv => {
            const b = EVENTO_BADGE[inv.evento_estado] ?? { bg: "bg-slate-100", text: "text-slate-600", label: inv.evento_estado };
            const cerrado = ["cancelado", "completado"].includes(inv.evento_estado);
            return (
              <div key={inv.id} className="flex flex-col rounded-card bg-white p-5 shadow-card ring-1 ring-slate-100">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h2 className="font-bold text-slate-800">{inv.evento_nombre}</h2>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${b.bg} ${b.text}`}>{b.label}</span>
                </div>
                <p className="text-xs text-slate-500">{inv.recinto_nombre}</p>
                <p className="mb-3 text-xs tabular text-slate-500">{fechaCorta(inv.vigencia_inicio)} → {fechaCorta(inv.vigencia_fin)}</p>
                <div className="mt-auto flex items-center justify-between">
                  <span className="text-sm text-slate-600">
                    Personal: <span className="font-semibold tabular text-slate-800">{inv.asignados}{inv.limite ? ` / ${inv.limite}` : ""}</span>
                  </span>
                  <button
                    onClick={() => abrirGestion(inv)}
                    disabled={cerrado}
                    className="rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
                    style={{ backgroundColor: "#2563EB" }}>
                    Gestionar personal
                  </button>
                </div>
                {inv.requiere_parking && (
                  <p className="mt-2 text-[11px] text-slate-400">🅿 {inv.parking || "Estacionamiento asignado"}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Modal gestión de empleados ─────────────────────────── */}
      {gestion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F1B2D]/40 p-4 py-6">
          <div className="flex max-h-full w-full max-w-2xl flex-col rounded-modal bg-white shadow-panel">
            <div className="flex items-start justify-between border-b border-slate-100 px-6 py-4">
              <div>
                <h2 className="text-base font-bold" style={{ color: INK }}>Personal del evento</h2>
                <p className="text-xs text-slate-500">{gestion.evento_nombre} · {gestion.recinto_nombre}</p>
              </div>
              <button onClick={() => { setGestion(null); setCand(null); }}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              {loadingCand || !cand ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
                </div>
              ) : (
                <div className="space-y-5">
                  {/* Detalles del evento */}
                  <div className="rounded-lg border border-slate-200 p-4">
                    <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Detalles del evento</p>
                    {gestion.evento_descripcion && (
                      <p className="mb-3 text-sm text-slate-600">{gestion.evento_descripcion}</p>
                    )}
                    <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                      <Detalle label="Recinto" valor={gestion.recinto_nombre} />
                      <Detalle label="Vigencia" valor={`${fechaCorta(gestion.vigencia_inicio)} → ${fechaCorta(gestion.vigencia_fin)}`} />
                      <Detalle label="Horario" valor={[gestion.hora_inicio, gestion.hora_fin].filter(Boolean).join(" – ") || "—"} />
                      <Detalle label="Zona" valor={gestion.zona_nombre || "—"} />
                      <Detalle label="Punto de acceso" valor={gestion.acceso_nombre || "—"} />
                      <Detalle label="Protocolo" valor={gestion.protocolo_nombre || "—"} />
                      {gestion.requiere_parking && (
                        <Detalle label="Estacionamiento" valor={gestion.parking || "Asignado"} />
                      )}
                      <Detalle label="Áreas autorizadas" valor={(gestion.areas_nombres && gestion.areas_nombres.length) ? gestion.areas_nombres.join(", ") : "—"} />
                    </div>
                  </div>

                  {/* Cupo */}
                  <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2.5 text-sm">
                    <span className="text-slate-600">Cupo</span>
                    <span className={`font-semibold tabular ${cupoLleno ? "text-red-600" : "text-slate-800"}`}>
                      {cand.asignados_count}{cand.limite ? ` / ${cand.limite}` : " (sin límite)"}
                    </span>
                  </div>

                  {aviso && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">{aviso}</div>
                  )}

                  {cand.requiere_documentos ? (
                    <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                      Este evento requiere documentos. Puedes agregar empleados aunque sus docs estén
                      pendientes — su acceso se confirma automáticamente cuando el recinto los verifique.
                    </p>
                  ) : (
                    <p className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-500">
                      Este evento no exige documentos. Puedes asignar a cualquier empleado activo.
                    </p>
                  )}

                  {/* Empleados */}
                  <div className="space-y-2">
                    {cand.empleados.length === 0 && (
                      <p className="py-6 text-center text-sm text-slate-400">No tienes empleados activos. Agrégalos en la sección Empleados.</p>
                    )}
                    {cand.empleados.map(emp => (
                      <EmpleadoFila
                        key={emp.id}
                        emp={emp}
                        epId={gestion.id}
                        cupoLleno={cupoLleno}
                        enAccion={accion === emp.id}
                        onAsignar={() => asignar(emp)}
                        onQuitar={() => quitar(emp)}
                        onSubido={recargarCand}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end border-t border-slate-100 px-6 py-4">
              <button onClick={() => { setGestion(null); setCand(null); }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* Fila de empleado: asignar / quitar / subir documentos faltantes. */
function EmpleadoFila({ emp, epId, cupoLleno, enAccion, onAsignar, onQuitar, onSubido }: {
  emp: Candidato; epId: number; cupoLleno: boolean; enAccion: boolean;
  onAsignar: () => void; onQuitar: () => void; onSubido: () => void;
}) {
  void epId;
  const [tipoSel, setTipoSel] = useState<number | "">("");
  const [subiendo, setSubiendo] = useState(false);
  const [errUp, setErrUp] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const subibles = tiposSubibles(emp);

  // Asignado y docs verificados = confirmado; asignado con docs pendientes = en revisión.
  const confirmado = emp.asignado && emp.statusdocs === 1;
  const pendienteDocs = emp.asignado && emp.statusdocs === 0;
  // Mostrar el panel de documentos si faltan docs, esté o no asignado.
  const mostrarDocs = !emp.cumple && emp.detalle.some(g => !g.ok);

  async function subir(file: File) {
    if (!tipoSel) { setErrUp("Elige el tipo de documento."); return; }
    setSubiendo(true); setErrUp("");
    const fd = new FormData();
    fd.append("empleado", String(emp.id));
    fd.append("tipo_documento", String(tipoSel));
    fd.append("archivo", file);
    try {
      await api.post("/api/documentos-empleado/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTipoSel("");
      if (fileRef.current) fileRef.current.value = "";
      onSubido();
    } catch (err: any) {
      const d = err?.response?.data;
      setErrUp(typeof d === "object" ? JSON.stringify(d) : "No se pudo subir el documento.");
    } finally { setSubiendo(false); }
  }

  return (
    <div className={`rounded-lg border p-3 ${pendienteDocs ? "border-amber-200 bg-amber-50/40" : "border-slate-200"}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-800">{emp.nombre}</p>
          {confirmado ? (
            <span className="text-[11px] font-semibold text-green-700">✓ Confirmado — acceso autorizado</span>
          ) : pendienteDocs ? (
            <span className="text-[11px] font-semibold text-amber-700">⏳ Registrado — documentos en revisión</span>
          ) : emp.cumple ? (
            <span className="text-[11px] font-medium text-slate-400">Listo para asignar</span>
          ) : (
            <span className="text-[11px] font-medium text-amber-700">Faltan documentos verificados</span>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          {emp.asignado ? (
            <button onClick={onQuitar} disabled={enAccion}
              className="rounded-lg border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50">
              {enAccion ? "…" : "Quitar"}
            </button>
          ) : (
            <button
              onClick={onAsignar}
              disabled={enAccion || cupoLleno}
              title={cupoLleno ? "Cupo lleno" : (!emp.cumple ? "Se agregará pendiente de verificación documental" : "")}
              className="rounded-lg px-3 py-1 text-xs font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
              style={{ backgroundColor: emp.cumple ? "#16A34A" : "#D97706" }}>
              {enAccion ? "…" : emp.cumple ? "Asignar" : "Agregar"}
            </button>
          )}
        </div>
      </div>

      {/* Detalle documental cuando faltan docs (asignado o no) */}
      {mostrarDocs && (
        <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          {emp.detalle.filter(g => !g.ok).map(g => (
            <div key={g.grupo} className="text-xs">
              <p className="font-semibold text-slate-600">
                {g.grupo_nombre}
                <span className="ml-1 font-normal text-slate-400">
                  ({g.type_validation === 1 ? "todos los documentos" : "al menos uno"})
                </span>
              </p>
              {g.pendientes.length > 0 && (
                <p className="text-amber-600">En verificación: {g.pendientes.join(", ")}</p>
              )}
              {g.faltantes.length > 0 && (
                <p className="text-slate-500">Faltan: {g.faltantes.join(", ")}</p>
              )}
            </div>
          ))}

          {subibles.length > 0 && (
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <select value={tipoSel} onChange={e => setTipoSel(e.target.value ? Number(e.target.value) : "")}
                className="h-8 rounded-lg border border-slate-200 bg-white px-2 text-xs">
                <option value="">Tipo de documento…</option>
                {subibles.map(t => <option key={t.id} value={t.id}>{t.nombre}</option>)}
              </select>
              <label className={`cursor-pointer rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 ${subiendo ? "opacity-50" : ""}`}>
                {subiendo ? "Subiendo…" : "Subir documento"}
                <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) subir(f); }} />
              </label>
              <span className="text-[11px] text-slate-400">Se envía a verificación del recinto.</span>
            </div>
          )}
          {errUp && <p className="text-[11px] text-red-500">{errUp}</p>}
        </div>
      )}
    </div>
  );
}
