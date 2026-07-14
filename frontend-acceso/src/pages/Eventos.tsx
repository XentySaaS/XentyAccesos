/**
 * Eventos — listado, CRUD completo y gestión de proveedores invitados.
 * Estructura basada en el sistema original (proyecto_original/pantallas/).
 */
import { FormEvent, useCallback, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

/* ── Tipos ──────────────────────────────────────────────────────── */
interface Recinto    { id: number; nombre: string; }
interface Zona       { id: number; nombre: string; recinto: number; }
interface Acceso     { id: number; nombre: string; recinto: number; }
interface Protocolo  { id: number; nombre: string; }
interface Proveedor  { id: number; nombre: string; nombre_responsable?: string; email_responsable?: string; }
interface Usuario    { id: number; nombre: string; rol: string; }
interface GrupoDoc   { id: number; nombre: string; }
interface AreaAut    { id: number; nombre: string; }

interface GrupoReq   { grupo: number; type_validation: number; }

interface Evento {
  id: number; nombre: string; descripcion?: string;
  recinto: number; protocolo?: number;
  vigencia_inicio: string; vigencia_fin: string;
  hora_inicio?: string; hora_fin?: string;
  estado: string;
  verificadores: number[];
  grupos_documentos?: GrupoReq[];
}
interface EventoProveedor {
  id: number; evento: number; proveedor: number; protocolo?: number;
  zona?: number; acceso?: number; limite?: number;
  requiere_parking: boolean; parking?: string; cajones_parking: number; notas?: string;
  areas_autorizadas?: number[];
  asignados: number;
  // campos mostrados (los provee el backend)
  proveedor_nombre?: string; zona_nombre?: string; acceso_nombre?: string;
}

/* ── Utilidades ──────────────────────────────────────────────────── */
function lista<T>(d: { results?: T[] } | T[]): T[] {
  return Array.isArray(d) ? d : (d.results ?? []);
}
function fmt(date: string) {
  if (!date) return "—";
  const [y, m, d] = date.split("-");
  const meses = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  return `${d} ${meses[Number(m) - 1]} ${y}`;
}

const ESTADO_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  programado: { bg: "bg-blue-50",   text: "text-blue-700",  label: "Programado" },
  en_curso:   { bg: "bg-green-50",  text: "text-green-700", label: "En curso"   },
  completado: { bg: "bg-slate-100", text: "text-slate-600", label: "Completado" },
  cancelado:  { bg: "bg-red-50",    text: "text-red-600",   label: "Cancelado"  },
};

/* ── Subcomponente: badge de estado ──────────────────────────────── */
function EstadoBadge({ estado }: { estado: string }) {
  const s = ESTADO_STYLE[estado] ?? { bg: "bg-slate-100", text: "text-slate-600", label: estado };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  );
}

/* ── Componente principal ────────────────────────────────────────── */
export default function Eventos() {
  /* catálogos */
  const [recintos,   setRecintos]   = useState<Recinto[]>([]);
  const [protocolos, setProtocolos] = useState<Protocolo[]>([]);
  const [usuarios,   setUsuarios]   = useState<Usuario[]>([]);
  const [grupos,     setGrupos]     = useState<GrupoDoc[]>([]);
  const [proveedores,setProveedores]= useState<Proveedor[]>([]);

  /* lista de eventos */
  const [items,   setItems]   = useState<Evento[]>([]);
  const [error,   setError]   = useState<string | null>(null);
  const [cargando,setCargando]= useState(true);

  /* modal crear / editar */
  const [modal, setModal] = useState<"" | "crear" | "editar">("");
  const [eventoSel, setEventoSel] = useState<Evento | null>(null);

  /* formulario de evento */
  const FORM_VACIO = {
    nombre: "", descripcion: "", recinto: "", protocolo: "",
    vigencia_inicio: "", vigencia_fin: "",
    hora_inicio: "", hora_fin: "", estado: "programado",
  };
  const [form, setForm] = useState(FORM_VACIO);
  const [verificadoresIds, setVerificadoresIds] = useState<number[]>([]);
  const [gruposReq, setGruposReq] = useState<GrupoReq[]>([]);

  /* sección proveedores (dentro de editar) */
  const [eventoProv,  setEventoProv]  = useState<EventoProveedor[]>([]);
  const [modalInv,    setModalInv]    = useState(false);
  const [invSel,      setInvSel]      = useState<EventoProveedor | null>(null);

  /* filtros dinámicos por recinto */
  const [zonas,    setZonas]    = useState<Zona[]>([]);
  const [accesos,  setAccesos]  = useState<Acceso[]>([]);
  const [areasAut, setAreasAut] = useState<AreaAut[]>([]);

  /* form invitación */
  const INV_VACIO = {
    proveedor: "", zona: "", acceso: "", protocolo: "", limite: "",
    requiere_parking: false, parking: "", cajones_parking: "1", notas: "",
  };
  const [inv, setInv]       = useState(INV_VACIO);
  const [invAreas, setInvAreas] = useState<number[]>([]);
  const [bajandoGafete, setBajandoGafete] = useState<number | null>(null);

  /* ── Carga de catálogos y eventos ─────────────────────────────── */
  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const [ev, rec, prot, usr, grp, prov] = await Promise.all([
        api.get("/api/eventos/"),
        api.get("/api/recintos/"),
        api.get("/api/protocolos/"),
        api.get("/api/usuarios/"),
        api.get("/api/grupos-documentos/").catch(() => ({ data: [] })),
        api.get("/api/proveedores/"),
      ]);
      setItems(lista(ev.data));
      setRecintos(lista(rec.data));
      setProtocolos(lista(prot.data));
      setUsuarios(lista(usr.data));
      setGrupos(lista(grp.data));
      setProveedores(lista(prov.data));
    } catch {
      setError("No se pudo cargar los datos.");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  /* ── Cargar proveedores del evento cuando se edita ─────────────── */
  async function cargarProveedoresEvento(eventoId: number) {
    const { data } = await api.get(`/api/evento-proveedores/?evento=${eventoId}`);
    const eps: EventoProveedor[] = lista(data);
    // Enriquecer con nombres
    setEventoProv(eps.map(ep => ({
      ...ep,
      proveedor_nombre: proveedores.find(p => p.id === ep.proveedor)?.nombre ?? String(ep.proveedor),
      zona_nombre: zonas.find(z => z.id === ep.zona)?.nombre,
      acceso_nombre: accesos.find(a => a.id === ep.acceso)?.nombre,
    })));
  }

  /* ── Cargar zonas/accesos/áreas por recinto ────────────────────── */
  async function cargarPorRecinto(recintoId: number) {
    const [z, a, ar] = await Promise.all([
      api.get(`/api/zonas/?recinto=${recintoId}`).catch(() => ({ data: [] })),
      api.get(`/api/accesos/?recinto=${recintoId}`).catch(() => ({ data: [] })),
      api.get(`/api/areas-autorizadas/?recinto=${recintoId}`).catch(() => ({ data: [] })),
    ]);
    setZonas(lista(z.data));
    setAccesos(lista(a.data));
    setAreasAut(lista(ar.data));
  }

  /* ── Abrir crear ──────────────────────────────────────────────── */
  function abrirCrear() {
    setForm(FORM_VACIO);
    setVerificadoresIds([]);
    setGruposReq([]);
    setEventoSel(null);
    setModal("crear");
  }

  /* ── Abrir editar ─────────────────────────────────────────────── */
  async function abrirEditar(ev: Evento) {
    setForm({
      nombre: ev.nombre,
      descripcion: ev.descripcion ?? "",
      recinto: String(ev.recinto),
      protocolo: ev.protocolo ? String(ev.protocolo) : "",
      vigencia_inicio: ev.vigencia_inicio,
      vigencia_fin: ev.vigencia_fin,
      hora_inicio: ev.hora_inicio ?? "",
      hora_fin: ev.hora_fin ?? "",
      estado: ev.estado,
    });
    setVerificadoresIds(ev.verificadores ?? []);
    setGruposReq(ev.grupos_documentos ?? []);   // precarga los grupos requeridos existentes
    setEventoSel(ev);
    if (ev.recinto) await cargarPorRecinto(ev.recinto);
    await cargarProveedoresEvento(ev.id);
    setModal("editar");
  }

  /* ── Guardar evento ───────────────────────────────────────────── */
  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const payload = {
      nombre: form.nombre,
      descripcion: form.descripcion || null,
      recinto: Number(form.recinto),
      protocolo: form.protocolo ? Number(form.protocolo) : null,
      vigencia_inicio: form.vigencia_inicio,
      vigencia_fin: form.vigencia_fin,
      hora_inicio: form.hora_inicio || null,
      hora_fin: form.hora_fin || null,
    };
    try {
      let id: number;
      if (modal === "crear") {
        const { data } = await api.post<Evento>("/api/eventos/", payload);
        id = data.id;
      } else {
        await api.patch(`/api/eventos/${eventoSel!.id}/`, payload);
        id = eventoSel!.id;
      }
      // Asignar verificadores
      if (verificadoresIds.length > 0) {
        await api.post(`/api/eventos/${id}/asignar_verificadores/`, { usuarios: verificadoresIds });
      }
      // Grupos de documentos
      if (gruposReq.length > 0) {
        await api.post(`/api/eventos/${id}/requisitos-documentos/`, { grupos: gruposReq });
      }
      setModal("");
      await cargar();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.response?.data?.vigencia_fin?.[0] ?? "No se pudo guardar.");
    }
  }

  /* ── Eliminar evento ──────────────────────────────────────────── */
  async function eliminar(ev: Evento) {
    if (!confirm(`¿Eliminar el evento "${ev.nombre}"? Esta acción no se puede deshacer.`)) return;
    try {
      await api.delete(`/api/eventos/${ev.id}/`);
      await cargar();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "No se pudo eliminar.");
    }
  }

  /* ── Transición de estado ─────────────────────────────────────── */
  async function transicion(ev: Evento, accion: "iniciar"|"completar"|"cancelar") {
    if (accion === "cancelar" && !confirm("Cancelar notificará a todos los proveedores del evento. ¿Continuar?")) return;
    try {
      await api.post(`/api/eventos/${ev.id}/${accion}/`);
      await cargar();
      if (eventoSel?.id === ev.id) {
        setEventoSel(items.find(i => i.id === ev.id) ?? null);
      }
    } catch {
      setError("Transición no permitida.");
    }
  }

  /* ── Guardar invitación de proveedor ─────────────────────────── */
  async function guardarInvitacion(e: FormEvent) {
    e.preventDefault();
    if (!eventoSel) return;
    setError(null);
    const payload = {
      evento: eventoSel.id,
      proveedor: Number(inv.proveedor),
      zona: inv.zona ? Number(inv.zona) : null,
      acceso: inv.acceso ? Number(inv.acceso) : null,
      protocolo: inv.protocolo ? Number(inv.protocolo) : null,
      limite: inv.limite ? Number(inv.limite) : 0,
      requiere_parking: inv.requiere_parking,
      parking: inv.requiere_parking ? (inv.parking || null) : null,
      cajones_parking: inv.requiere_parking ? Number(inv.cajones_parking) : 0,
      notas: inv.notas || null,
      areas_autorizadas: invAreas,
    };
    try {
      if (invSel) {
        await api.patch(`/api/evento-proveedores/${invSel.id}/`, payload);
      } else {
        await api.post("/api/evento-proveedores/", payload);
      }
      setModalInv(false);
      setInvSel(null);
      setInv(INV_VACIO);
      await cargarProveedoresEvento(eventoSel.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "No se pudo guardar la invitación.");
    }
  }

  async function eliminarInvitacion(ep: EventoProveedor) {
    if (!confirm(`¿Quitar a "${ep.proveedor_nombre}" del evento?`)) return;
    await api.delete(`/api/evento-proveedores/${ep.id}/`);
    if (eventoSel) cargarProveedoresEvento(eventoSel.id);
  }

  function abrirNuevaInv() {
    setInv({ ...INV_VACIO });
    setInvAreas([]);
    setInvSel(null);
    setModalInv(true);
  }

  function abrirEditarInv(ep: EventoProveedor) {
    setInv({
      proveedor: String(ep.proveedor),
      zona: ep.zona ? String(ep.zona) : "",
      acceso: ep.acceso ? String(ep.acceso) : "",
      protocolo: ep.protocolo ? String(ep.protocolo) : "",
      limite: ep.limite ? String(ep.limite) : "",
      requiere_parking: ep.requiere_parking,
      parking: ep.parking ?? "",
      cajones_parking: String(ep.cajones_parking || 1),
      notas: ep.notas ?? "",
    });
    setInvAreas(ep.areas_autorizadas ?? []);
    setInvSel(ep);
    setModalInv(true);
  }

  /* ── Descargar gafete de estacionamiento (QR cifrado, tarjeta compuesta) ── */
  async function descargarGafeteParking(ep: EventoProveedor) {
    setBajandoGafete(ep.id);
    try {
      const r = await api.get(`/api/evento-proveedores/${ep.id}/gafete-parking/`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      setError("No se pudo generar el gafete de estacionamiento.");
    } finally {
      setBajandoGafete(null);
    }
  }

  /* ── Toggle verificador ──────────────────────────────────────── */
  function toggleVerificador(uid: number) {
    setVerificadoresIds(prev =>
      prev.includes(uid) ? prev.filter(v => v !== uid) : [...prev, uid]
    );
  }

  /* ── Helpers grupos de documentos ────────────────────────────── */
  function addGrupo() {
    setGruposReq(prev => [...prev, { grupo: 0, type_validation: 0 }]);
  }
  function removeGrupo(i: number) {
    setGruposReq(prev => prev.filter((_, idx) => idx !== i));
  }
  function updateGrupo(i: number, field: keyof GrupoReq, val: number) {
    setGruposReq(prev => prev.map((g, idx) => idx === i ? { ...g, [field]: val } : g));
  }

  /* ── Render ──────────────────────────────────────────────────── */
  return (
    <div className="space-y-5">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Eventos › Listado</p>
          <h1 className="mt-0.5 text-[22px] font-extrabold tracking-tight text-ink-900">Eventos</h1>
        </div>
        <button
          onClick={abrirCrear}
          className="rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
          style={{ backgroundColor: "#2563EB" }}
        >
          + Crear evento
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button className="ml-3 underline" onClick={() => setError(null)}>Cerrar</button>
        </div>
      )}

      {/* Tabla */}
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
              <tr>
                <td colSpan={5} className="px-5 py-10 text-center text-slate-400">
                  Aún no hay eventos. Crea el primero.
                </td>
              </tr>
            )}
            {items.map((ev) => {
              const rec = recintos.find(r => r.id === ev.recinto);
              return (
                <tr key={ev.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="tabular px-5 py-3 text-slate-500">{fmt(ev.vigencia_inicio)}</td>
                  <td className="px-5 py-3 font-medium text-ink-900">{ev.nombre}</td>
                  <td className="px-5 py-3">
                    {rec && (
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
                        {rec.nombre}
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3"><EstadoBadge estado={ev.estado} /></td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-3">
                      {/* Transiciones rápidas */}
                      {ev.estado === "programado" && (
                        <button onClick={() => transicion(ev,"iniciar")}
                          className="text-xs text-blue-600 hover:underline">Iniciar</button>
                      )}
                      {ev.estado === "en_curso" && (
                        <button onClick={() => transicion(ev,"completar")}
                          className="text-xs text-green-600 hover:underline">Completar</button>
                      )}
                      {(ev.estado === "programado" || ev.estado === "en_curso") && (
                        <button onClick={() => transicion(ev,"cancelar")}
                          className="text-xs text-red-500 hover:underline">Cancelar</button>
                      )}
                      {ev.estado !== "cancelado" && (
                        <button onClick={() => abrirEditar(ev)}
                          className="rounded border border-slate-200 px-3 py-1 text-xs font-medium text-signal-600 hover:bg-signal-50 transition-colors"
                          style={{ color: "#2563EB" }}>
                          ✎ Editar
                        </button>
                      )}
                      <button onClick={() => eliminar(ev)}
                        className="rounded border border-red-100 px-3 py-1 text-xs font-medium text-red-500 hover:bg-red-50 transition-colors">
                        ✕ Borrar
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="border-t border-slate-100 px-5 py-2.5 text-xs text-slate-400">
          Se muestran {items.length} resultado{items.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* ── Modal crear / editar ───────────────────────────────── */}
      {(modal === "crear" || modal === "editar") && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 py-8 px-4">
          <div className="w-full max-w-2xl rounded-modal bg-white shadow-panel">
            {/* Header modal */}
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <h2 className="text-base font-bold text-ink-900">
                {modal === "crear" ? "Crear evento" : "Editar evento"}
              </h2>
              <button onClick={() => setModal("")}
                className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <form onSubmit={guardar}>
              <div className="space-y-5 px-6 py-5">
                {/* Fila 1 */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-nombre" className="text-sm font-medium text-slate-700">
                        Nombre del evento <span className="text-red-500">*</span>
                      </label>
                      <Ayuda>Nombre público del evento: aparece en gafetes, correos de invitación y la bitácora de acceso.</Ayuda>
                    </div>
                    <input id="ev-nombre" required value={form.nombre} onChange={e => setForm({...form, nombre: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-signal-600 focus:outline-none focus:ring-1 focus:ring-signal-600"
                      style={{ "--tw-ring-color": "#2563EB" } as any} />
                  </div>
                  <div className="col-span-2">
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-descripcion" className="text-sm font-medium text-slate-700">Descripción</label>
                      <Ayuda>Detalle interno del evento para el equipo de operación. No se muestra en el gafete ni al proveedor.</Ayuda>
                    </div>
                    <textarea id="ev-descripcion" value={form.descripcion} onChange={e => setForm({...form, descripcion: e.target.value})}
                      rows={2}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-signal-600 focus:outline-none focus:ring-1 focus:ring-signal-600" />
                  </div>
                </div>

                {/* Fila 2 */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-recinto" className="text-sm font-medium text-slate-700">
                        Recinto <span className="text-red-500">*</span>
                      </label>
                      <Ayuda>El inmueble donde se realiza el evento. Determina qué zonas, puntos de acceso y áreas autorizadas puedes ofrecer a los proveedores invitados.</Ayuda>
                    </div>
                    <select id="ev-recinto" required value={form.recinto}
                      onChange={e => { setForm({...form, recinto: e.target.value}); if(e.target.value) cargarPorRecinto(Number(e.target.value)); }}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-signal-600 focus:outline-none">
                      <option value="">Seleccione una opción</option>
                      {recintos.map(r => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                    </select>
                  </div>
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-fecha" className="text-sm font-medium text-slate-700">
                        Fecha del evento <span className="text-red-500">*</span>
                      </label>
                      <Ayuda>Día en que se realiza el evento. Es el mismo valor que "Vigencia del acceso desde" — define desde cuándo el escáner acepta los gafetes.</Ayuda>
                    </div>
                    <input id="ev-fecha" required type="date" value={form.vigencia_inicio}
                      onChange={e => setForm({...form, vigencia_inicio: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-signal-600 focus:outline-none" />
                  </div>
                </div>

                {/* Fila 3 */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-vig-desde" className="text-sm font-medium text-slate-700">
                        Vigencia del acceso desde <span className="text-red-500">*</span>
                      </label>
                      <Ayuda>Primer día en que los QR de este evento permiten el acceso. Antes de esta fecha, el escáner rechaza cualquier gafete del evento.</Ayuda>
                    </div>
                    <input id="ev-vig-desde" required type="date" value={form.vigencia_inicio}
                      onChange={e => setForm({...form, vigencia_inicio: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                  </div>
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-vig-hasta" className="text-sm font-medium text-slate-700">
                        Vigencia del acceso hasta <span className="text-red-500">*</span>
                      </label>
                      <Ayuda>Último día en que los QR de este evento permiten el acceso. Después de esta fecha, el escáner rechaza los gafetes aunque la persona siga invitada.</Ayuda>
                    </div>
                    <input id="ev-vig-hasta" required type="date" value={form.vigencia_fin}
                      onChange={e => setForm({...form, vigencia_fin: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                  </div>
                </div>

                {/* Fila 4 */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-hora-inicio" className="text-sm font-medium text-slate-700">Hora de inicio</label>
                      <Ayuda>Solo informativa: el escáner valida por día de vigencia, no por hora exacta.</Ayuda>
                    </div>
                    <input id="ev-hora-inicio" type="time" value={form.hora_inicio}
                      onChange={e => setForm({...form, hora_inicio: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                  </div>
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-hora-fin" className="text-sm font-medium text-slate-700">Hora de fin</label>
                      <Ayuda>Solo informativa: el escáner valida por día de vigencia, no por hora exacta.</Ayuda>
                    </div>
                    <input id="ev-hora-fin" type="time" value={form.hora_fin}
                      onChange={e => setForm({...form, hora_fin: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                  </div>
                </div>

                {/* Fila 5 */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-protocolo" className="text-sm font-medium text-slate-700">Protocolo</label>
                      <Ayuda>Protocolo de seguridad u operación del recinto asociado a este evento (p. ej. plan de evacuación o lineamientos de ingreso).</Ayuda>
                    </div>
                    <select id="ev-protocolo" value={form.protocolo} onChange={e => setForm({...form, protocolo: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                      <option value="">Seleccione una opción</option>
                      {protocolos.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                    </select>
                  </div>
                  <div>
                    <div className="mb-1 flex items-center gap-1.5">
                      <label htmlFor="ev-estado" className="text-sm font-medium text-slate-700">Estado</label>
                      <Ayuda>Ciclo de vida del evento. "Cancelado" o "Completado" bloquean el acceso en el escáner aunque la vigencia siga activa — normalmente se cambia con los botones Iniciar/Completar/Cancelar de la tabla, no aquí.</Ayuda>
                    </div>
                    <select id="ev-estado" value={form.estado} onChange={e => setForm({...form, estado: e.target.value})}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                      <option value="programado">Programado</option>
                      <option value="en_curso">En curso</option>
                      <option value="completado">Completado</option>
                      <option value="cancelado">Cancelado</option>
                    </select>
                  </div>
                </div>

                {/* Verificadores */}
                <div>
                  <div className="mb-2 flex items-center gap-1.5">
                    <span className="text-sm font-medium text-slate-700">Verificadores</span>
                    <Ayuda>Usuarios que pueden revisar y aprobar los documentos que suben los proveedores invitados a este evento.</Ayuda>
                  </div>
                  <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 p-3">
                    {usuarios
                      .filter(u => ["administrador","verificador","editor"].includes(u.rol))
                      .map(u => (
                        <button
                          key={u.id} type="button"
                          onClick={() => toggleVerificador(u.id)}
                          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors border ${
                            verificadoresIds.includes(u.id)
                              ? "border-signal-600 bg-signal-50 text-signal-600"
                              : "border-slate-200 text-slate-500 hover:border-slate-300"
                          }`}
                          style={verificadoresIds.includes(u.id) ? { borderColor: "#2563EB", color: "#2563EB", backgroundColor: "#EFF6FF" } : {}}
                        >
                          {verificadoresIds.includes(u.id) ? "✓ " : ""}{u.nombre}
                        </button>
                      ))}
                    {usuarios.filter(u => ["administrador","verificador","editor"].includes(u.rol)).length === 0 && (
                      <p className="text-xs text-slate-400">Sin usuarios disponibles</p>
                    )}
                  </div>
                </div>

                {/* Grupos de documentos */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-medium text-slate-700">Grupo de documentos</span>
                      <Ayuda>Conjunto de documentos que el proveedor debe subir para este evento (p. ej. seguros, identificaciones, constancias).</Ayuda>
                    </div>
                    <button type="button" onClick={addGrupo}
                      className="text-xs font-medium hover:underline"
                      style={{ color: "#2563EB" }}>
                      + Añadir grupo
                    </button>
                  </div>
                  {gruposReq.length === 0 && (
                    <p className="rounded-lg border border-dashed border-slate-200 px-4 py-3 text-center text-xs text-slate-400">
                      Sin grupos de documentos requeridos.
                    </p>
                  )}
                  {gruposReq.map((g, i) => (
                    <div key={i} className="mb-2 grid grid-cols-[1fr_1fr_auto] items-end gap-3">
                      <div>
                        <div className="mb-1 flex items-center gap-1.5">
                          <label htmlFor={`ev-grupo-${i}`} className="text-xs font-medium text-slate-600">
                            Grupo de documentos <span className="text-red-500">*</span>
                          </label>
                          <Ayuda>Catálogo de documentos que aplica a esta invitación (definido en Catálogos › Grupos de documentos).</Ayuda>
                        </div>
                        <select id={`ev-grupo-${i}`} value={g.grupo} onChange={e => updateGrupo(i, "grupo", Number(e.target.value))}
                          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                          <option value={0}>Seleccione una opción</option>
                          {grupos.map(gr => <option key={gr.id} value={gr.id}>{gr.nombre}</option>)}
                        </select>
                      </div>
                      <div>
                        <div className="mb-1 flex items-center gap-1.5">
                          <label htmlFor={`ev-tipoval-${i}`} className="text-xs font-medium text-slate-600">
                            Tipo de validación <span className="text-red-500">*</span>
                          </label>
                          <Ayuda>"Cualquiera que se presente" aprueba con un solo documento del grupo. "Todos los documentos" exige subir todos antes de marcar como cumplido.</Ayuda>
                        </div>
                        <select id={`ev-tipoval-${i}`} value={g.type_validation} onChange={e => updateGrupo(i, "type_validation", Number(e.target.value))}
                          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                          <option value={0}>Cualquiera que se presente</option>
                          <option value={1}>Todos los documentos</option>
                        </select>
                      </div>
                      <button type="button" onClick={() => removeGrupo(i)}
                        className="mb-0.5 rounded p-1.5 text-red-400 hover:bg-red-50">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path d="M3 6h18M19 6l-1 14H6L5 6M10 11v6M14 11v6M9 6V4h6v2"/>
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Acciones del form */}
              <div className="flex items-center justify-end gap-3 border-t border-slate-100 px-6 py-4">
                <button type="button" onClick={() => setModal("")}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">
                  Cancelar
                </button>
                <button type="submit"
                  className="rounded-lg px-5 py-2 text-sm font-semibold text-white"
                  style={{ backgroundColor: "#2563EB" }}>
                  {modal === "crear" ? "Crear evento" : "Guardar cambios"}
                </button>
              </div>
            </form>

            {/* ── Sección Proveedores (solo en editar) ─────────── */}
            {modal === "editar" && eventoSel && (
              <div className="border-t border-slate-100 px-6 pb-6">
                <div className="mb-3 mt-5 flex items-center justify-between">
                  <h3 className="text-base font-bold text-ink-900">Proveedores</h3>
                  <button
                    type="button"
                    onClick={abrirNuevaInv}
                    className="rounded-lg px-4 py-1.5 text-sm font-semibold text-white"
                    style={{ backgroundColor: "#2563EB" }}
                  >
                    Enviar invitaciones
                  </button>
                </div>

                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                      <th className="pb-2">Proveedor</th>
                      <th className="pb-2">Recinto</th>
                      <th className="pb-2">Zona</th>
                      <th className="pb-2">Personas</th>
                      <th className="pb-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {eventoProv.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-xs text-slate-400">
                          Sin proveedores invitados. Usa "Enviar invitaciones" para agregar.
                        </td>
                      </tr>
                    )}
                    {eventoProv.map(ep => {
                      const rec = recintos.find(r => r.id === eventoSel.recinto);
                      return (
                        <tr key={ep.id}>
                          <td className="py-2 font-medium" style={{ color: "#2563EB" }}>
                            {ep.proveedor_nombre}
                          </td>
                          <td className="py-2 text-slate-500">{rec?.nombre ?? "—"}</td>
                          <td className="py-2 text-slate-500">{ep.zona_nombre ?? "—"}</td>
                          <td className="tabular py-2 text-slate-500">{ep.asignados ?? 0}</td>
                          <td className="py-2 text-right">
                            {ep.requiere_parking && (
                              <button onClick={() => descargarGafeteParking(ep)} disabled={bajandoGafete === ep.id}
                                className="mr-3 text-xs font-medium text-slate-500 hover:text-slate-700 disabled:opacity-50">
                                {bajandoGafete === ep.id ? "Generando…" : "⬇ Pase parking"}
                              </button>
                            )}
                            <button onClick={() => abrirEditarInv(ep)}
                              className="mr-3 text-xs font-medium" style={{ color: "#2563EB" }}>
                              ✎ Editar
                            </button>
                            <button onClick={() => eliminarInvitacion(ep)}
                              className="text-xs font-medium text-red-500">
                              ✕ Borrar
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {eventoProv.length > 0 && (
                  <p className="mt-2 text-xs text-slate-400">
                    Se muestran de 1 a {eventoProv.length} de {eventoProv.length} resultados
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Modal Enviar Invitaciones ─────────────────────────── */}
      {modalInv && eventoSel && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 px-4 py-8">
          <form
            onSubmit={guardarInvitacion}
            className="w-full max-w-2xl overflow-y-auto rounded-modal bg-white shadow-panel"
            style={{ maxHeight: "90vh" }}
          >
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <h2 className="text-base font-bold text-ink-900">
                {invSel ? "Editar invitación del proveedor" : "Enviar invitaciones a proveedores"}
              </h2>
              <button type="button" onClick={() => { setModalInv(false); setInvSel(null); }}
                className="rounded p-1 text-slate-400 hover:bg-slate-100">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-x-6 gap-y-4 px-6 py-5">
              {/* Columna izquierda */}
              <div className="space-y-4">
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Nombre del evento</span>
                  <input value={eventoSel.nombre} disabled
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400" />
                </label>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="inv-proveedor" className="text-sm font-medium text-slate-700">
                      Proveedor <span className="text-red-500">*</span>
                    </label>
                    <Ayuda>Empresa proveedora que recibirá la invitación por correo, con el gafete QR para sus empleados asignados.</Ayuda>
                  </div>
                  <select id="inv-proveedor" required value={inv.proveedor} onChange={e => setInv({...inv, proveedor: e.target.value})}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-signal-600 focus:outline-none">
                    <option value="">Seleccione una opción</option>
                    {proveedores.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                  </select>
                </div>
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Recinto</span>
                  <input value={recintos.find(r => r.id === eventoSel.recinto)?.nombre ?? "—"} disabled
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400" />
                </label>
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Vigencia desde el</span>
                  <input value={eventoSel.vigencia_inicio} disabled
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400" />
                </label>
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Fecha del evento</span>
                  <input value={eventoSel.vigencia_inicio} disabled
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400" />
                </label>
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Vigencia hasta el</span>
                  <input value={eventoSel.vigencia_fin} disabled
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400" />
                </label>
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Responsable del proveedor</span>
                  <input
                    value={proveedores.find(p => p.id === Number(inv.proveedor))?.nombre_responsable ?? "No asignado"}
                    disabled
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400" />
                </label>
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Email del responsable</span>
                  <input
                    value={proveedores.find(p => p.id === Number(inv.proveedor))?.email_responsable ?? "No asignado"}
                    disabled
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400" />
                </label>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="inv-notas" className="text-sm font-medium text-slate-700">Notas adicionales</label>
                    <Ayuda>Instrucciones o comentarios que se incluyen en el correo de invitación que recibe el proveedor.</Ayuda>
                  </div>
                  <textarea id="inv-notas" value={inv.notas} onChange={e => setInv({...inv, notas: e.target.value})}
                    rows={3}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                </div>
              </div>

              {/* Columna derecha */}
              <div className="space-y-4">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="inv-zona" className="text-sm font-medium text-slate-700">
                      Zona <span className="text-red-500">*</span>
                    </label>
                    <Ayuda>Área del recinto a la que el proveedor tendrá acceso (p. ej. Cancha, VIP, Staff). Define el color y la etiqueta del gafete.</Ayuda>
                  </div>
                  <select id="inv-zona" value={inv.zona} onChange={e => setInv({...inv, zona: e.target.value})}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <option value="">Selecciona una zona</option>
                    {zonas.map(z => <option key={z.id} value={z.id}>{z.nombre}</option>)}
                  </select>
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="inv-acceso" className="text-sm font-medium text-slate-700">
                      Punto de acceso <span className="text-red-500">*</span>
                    </label>
                    <Ayuda>Entrada física por la que el proveedor debe ingresar. Se imprime en el gafete como referencia para el guardia.</Ayuda>
                  </div>
                  <select id="inv-acceso" value={inv.acceso} onChange={e => setInv({...inv, acceso: e.target.value})}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <option value="">Selecciona un punto de acceso</option>
                    {accesos.map(a => <option key={a.id} value={a.id}>{a.nombre}</option>)}
                  </select>
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="inv-limite" className="text-sm font-medium text-slate-700">
                      Número de personas invitadas <span className="text-red-500">*</span>
                    </label>
                    <Ayuda>Cupo máximo de empleados que este proveedor puede registrar para el evento. Usa 0 para no poner límite.</Ayuda>
                  </div>
                  <input id="inv-limite" type="number" min={1} value={inv.limite}
                    onChange={e => setInv({...inv, limite: e.target.value})}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="inv-protocolo" className="text-sm font-medium text-slate-700">
                      Protocolo <span className="text-red-500">*</span>
                    </label>
                    <Ayuda>Protocolo de seguridad específico para esta invitación, si difiere del protocolo general del evento.</Ayuda>
                  </div>
                  <select id="inv-protocolo" value={inv.protocolo} onChange={e => setInv({...inv, protocolo: e.target.value})}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <option value="">Selecciona un protocolo</option>
                    {protocolos.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                  </select>
                </div>

                {/* Toggle estacionamiento */}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setInv({...inv, requiere_parking: !inv.requiere_parking})}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${
                      inv.requiere_parking ? "bg-[#2563EB]" : "bg-slate-200"
                    }`}
                  >
                    <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                      inv.requiere_parking ? "translate-x-5" : "translate-x-0"
                    }`} />
                  </button>
                  <span className="text-sm font-medium text-slate-700">¿Asignar estacionamiento?</span>
                  <Ayuda>Actívalo si el proveedor necesita cajones de estacionamiento — se generarán pases con su propio QR, independientes del gafete de acceso peatonal.</Ayuda>
                </div>

                {inv.requiere_parking && (
                  <>
                    <div>
                      <div className="mb-1 flex items-center gap-1.5">
                        <label htmlFor="inv-parking-nombre" className="text-sm font-medium text-slate-700">
                          Nombre de estacionamiento <span className="text-red-500">*</span>
                        </label>
                        <Ayuda>Nombre del estacionamiento o zona vehicular asignada; se imprime en el pase de estacionamiento.</Ayuda>
                      </div>
                      <input id="inv-parking-nombre" value={inv.parking} onChange={e => setInv({...inv, parking: e.target.value})}
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                    </div>
                    <div>
                      <div className="mb-1 flex items-center gap-1.5">
                        <label htmlFor="inv-cajones" className="text-sm font-medium text-slate-700">
                          Cajones asignados <span className="text-red-500">*</span>
                        </label>
                        <Ayuda>Cantidad de cajones reservados para el proveedor. Se genera un pase QR de estacionamiento independiente por cada cajón.</Ayuda>
                      </div>
                      <input id="inv-cajones" type="number" min={1} value={inv.cajones_parking}
                        onChange={e => setInv({...inv, cajones_parking: e.target.value})}
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
                    </div>
                  </>
                )}

                {/* Áreas autorizadas (multi) */}
                <div className="text-sm">
                  <div className="mb-1 flex items-center gap-1.5">
                    <span className="font-medium text-slate-700">Áreas autorizadas</span>
                    <Ayuda>Áreas específicas del recinto donde el proveedor puede circular, además de su zona asignada.</Ayuda>
                  </div>
                  <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 p-3">
                    {areasAut.length === 0 && (
                      <p className="text-xs text-slate-400">El recinto no tiene áreas autorizadas registradas.</p>
                    )}
                    {areasAut.map(a => {
                      const on = invAreas.includes(a.id);
                      return (
                        <button key={a.id} type="button"
                          onClick={() => setInvAreas(prev => on ? prev.filter(x => x !== a.id) : [...prev, a.id])}
                          className="rounded-full border px-3 py-1 text-xs font-medium transition-colors"
                          style={on
                            ? { borderColor: "#2563EB", color: "#2563EB", backgroundColor: "#EFF6FF" }
                            : { borderColor: "#E2E8F0", color: "#64748B" }}>
                          {on ? "✓ " : ""}{a.nombre}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-slate-100 px-6 py-4">
              <button type="button" onClick={() => { setModalInv(false); setInvSel(null); }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit"
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white"
                style={{ backgroundColor: "#2563EB" }}>
                {invSel ? "Guardar cambios" : "Enviar invitación"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
