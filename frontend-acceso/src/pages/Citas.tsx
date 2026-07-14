/**
 * Citas — agenda de visitas programadas y walk-ins.
 *
 * Flujos:
 *  - Nueva cita programada (tipo 0=Proveedor o 1=Directa)
 *  - Walk-in (tipo_cita=walk_in, crear directo sin abrir modal largo)
 *  - Ver detalle con asistentes
 *  - Confirmar / Cancelar estado
 *  - Eliminar (guarda: cita directa con asistentes o proveedor con empleados no se puede borrar)
 */
import { FormEvent, ReactNode, useCallback, useEffect, useRef, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

/**
 * Ayuda contextual por etiqueta de campo (ver docs/AYUDA_CONTEXTUAL.md). El componente Field
 * la resuelve por su `label`, así ambos formularios (crear/editar) heredan la misma ayuda sin
 * repetir texto en cada uso.
 */
const AYUDA_CITA: Record<string, string> = {
  "Nombre / motivo *": "Título de la cita: identifica la visita en la agenda, el gafete y la bitácora (p. ej. \"Mantenimiento aire acondicionado\").",
  "Tipo de cita": "Programada: agendada con anticipación. Walk-in: visita sin cita previa registrada al momento. Emergencia: ingreso urgente.",
  "Estado": "Ciclo de la cita. \"Cancelada\" bloquea el acceso en el escáner aunque el invitado tenga su QR.",
  "Fecha *": "Día de la visita. El escáner solo permite el acceso ese día exacto (la cita no tiene rango de vigencia).",
  "Hora inicio": "Hora prevista de llegada. Informativa: el escáner valida por día, no por hora.",
  "Hora fin": "Hora prevista de salida. Informativa: el escáner valida por día, no por hora.",
  "Asignado a": "Usuario del recinto responsable de atender la visita.",
  "Detalles": "Notas internas sobre el objetivo de la visita (opcional).",
  "Recinto *": "Inmueble donde ocurre la cita. Determina qué zonas, ubicaciones y puntos de acceso puedes elegir abajo.",
  "Zona": "Área del recinto a la que el invitado tendrá acceso.",
  "Ubicación": "Punto específico dentro de la zona (oficina, sala) destino de la visita.",
  "Punto de acceso": "Entrada física por la que ingresa el invitado; se imprime en el gafete como referencia para el guardia.",
  "Protocolo": "Protocolo de seguridad u operación del recinto aplicable a esta cita.",
};

/* ── Tipos ──────────────────────────────────────────────────────────────── */
interface Recinto   { id: number; nombre: string; }
interface Zona      { id: number; nombre: string; recinto: number; }
interface Ubicacion { id: number; nombre: string; zona: number; }
interface Acceso    { id: number; nombre: string; recinto: number; }
interface Protocolo { id: number; nombre: string; }
interface Usuario   { id: number; nombre: string; email: string; rol: string; }

interface Persona {
  id: number; tipo: number; nombre: string;
  email: string; telefono: string; empresa: string; label: string;
}

interface Asistente {
  id: number; nombre: string; email: string; telefono: string;
  tipo: number; estado: number; ine_capturado: boolean;
}

interface CitaRow {
  id: number; nombre: string; fecha: string;
  hora_inicio: string; hora_fin: string;
  tipo: number; tipo_cita: string; estado: string;
  recinto: number; recinto_nombre: string;
  proveedor: number | null; proveedor_nombre: string | null;
  asignado_a: number | null; asignado_a_nombre: string | null;
  total_asistentes: number;
}

interface CitaDetalle extends CitaRow {
  detalles: string; limite: number | null;
  ubicacion: number | null; ubicacion_nombre: string | null; ubicacion_zona_id: number | null;
  acceso: number | null; acceso_nombre: string | null;
  protocolo: number | null; protocolo_nombre: string | null;
  asistentes: Asistente[];
}

/* ── Constantes ─────────────────────────────────────────────────────────── */
const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const TIPO_LABEL: Record<number, string> = { 0: "Proveedor", 1: "Directa" };
const TIPO_CITA_LABEL: Record<string, string> = {
  programada: "Programada", walk_in: "Walk-in", emergencia: "Emergencia",
};
const ESTADO_BADGE: Record<string, { bg: string; text: string }> = {
  pendiente:  { bg: "bg-amber-100",  text: "text-amber-800"  },
  confirmada: { bg: "bg-green-100",  text: "text-green-700"  },
  cancelada:  { bg: "bg-red-100",    text: "text-red-700"    },
};
const TIPO_CITA_BADGE: Record<string, { bg: string; text: string }> = {
  programada: { bg: "bg-blue-50",   text: "text-blue-700"   },
  walk_in:    { bg: "bg-violet-50", text: "text-violet-700" },
  emergencia: { bg: "bg-orange-50", text: "text-orange-700" },
};
const ASISTENTE_ESTADO: Record<number, string> = {
  0: "Pendiente", 1: "Confirmado", 2: "Cancelado",
};

/* ── Utilidades ─────────────────────────────────────────────────────────── */
function lista<T>(d: { results?: T[] } | T[]): T[] {
  return Array.isArray(d) ? d : (d.results ?? []);
}
function fmtFecha(s: string) {
  if (!s) return "—";
  const [y, m, d] = s.split("-");
  const meses = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  return `${d} ${meses[Number(m) - 1]} ${y}`;
}
function fmtHora(s: string) {
  return s ? s.slice(0, 5) : "—";
}

/* ── Invitado vacío ─────────────────────────────────────────────────────── */
const INVITADO_VACIO = { nombre: "", email: "", telefono: "", persona_id: null as number | null, tipo: 0 };

/* ── Formulario vacío ───────────────────────────────────────────────────── */
// tipo siempre 1 (Directa) — equivalente al hidden del sistema original
const FORM_VACIO = {
  nombre: "", detalles: "", fecha: "",
  hora_inicio: "", hora_fin: "",
  tipo_cita: "programada",
  estado: "pendiente",
  recinto: "",
  zona_sel: "",      // solo para cascade, no se envía al backend
  ubicacion: "",
  acceso: "",
  protocolo: "",
  asignado_a: "",
};

type ModalMode = "crear" | "detalle" | "editar" | null;

/* ══════════════════════════════════════════════════════════════════════════
   Componente principal
   ══════════════════════════════════════════════════════════════════════════ */
export default function Citas() {
  /* catálogos */
  const [recintos,   setRecintos]   = useState<Recinto[]>([]);
  const [protocolos, setProtocolos] = useState<Protocolo[]>([]);
  const [usuarios,   setUsuarios]   = useState<Usuario[]>([]);

  /* cascada en formulario */
  const [zonas,      setZonas]      = useState<Zona[]>([]);
  const [ubicaciones,setUbicaciones]= useState<Ubicacion[]>([]);
  const [accesos,    setAccesos]    = useState<Acceso[]>([]);

  /* lista */
  const [citas,   setCitas]   = useState<CitaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState("");
  const [filtroTipo,   setFiltroTipo]   = useState("");

  /* modales */
  const [modal,   setModal]   = useState<ModalMode>(null);
  const [detalle, setDetalle] = useState<CitaDetalle | null>(null);
  const [detLoading, setDetLoading] = useState(false);

  /* formulario */
  const [form,     setForm]     = useState(FORM_VACIO);
  const [invitados, setInvitados] = useState([{ ...INVITADO_VACIO }]);
  const [saving,   setSaving]   = useState(false);
  const [error,    setError]    = useState("");
  const [citaEditId, setCitaEditId] = useState<number | null>(null);

  /* reenvío de invitación */
  const [reenviando,    setReenviando]    = useState<number | null>(null);
  const [reenviandoMsg, setReenviandoMsg] = useState<{ id: number; tipo: "ok" | "err"; texto: string } | null>(null);

  /* agregar / dar de baja invitados desde el detalle */
  const [agregando,  setAgregando]  = useState(false);
  const [agregarMsg, setAgregarMsg] = useState("");
  const [asistBusy,  setAsistBusy]  = useState<number | null>(null);

  /* autocomplete invitados */
  const [, setQuery]    = useState("");
  const [sugs,     setSugs]     = useState<Persona[]>([]);
  const [sugIdx,   setSugIdx]   = useState<number | null>(null); // índice del invitado activo
  const debRef = useRef<ReturnType<typeof setTimeout>>();

  /* ── Cargar catálogos ─────────────────────────────────────────────── */
  const cargarCatalogos = useCallback(() => {
    Promise.all([
      api.get("/api/recintos/"),
      api.get("/api/protocolos/"),
      api.get("/api/usuarios/"),
    ]).then(([r, p, u]) => {
      setRecintos(lista(r.data));
      setProtocolos(lista(p.data));
      setUsuarios(lista(u.data));
    }).catch(() => {});
  }, []);

  /* ── Cargar citas ─────────────────────────────────────────────────── */
  const cargar = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (filtroEstado) params.estado = filtroEstado;
    if (filtroTipo)   params.tipo   = filtroTipo;
    api.get("/api/citas/", { params })
      .then(r => setCitas(lista(r.data)))
      .finally(() => setLoading(false));
  }, [filtroEstado, filtroTipo]);

  useEffect(() => { cargarCatalogos(); }, [cargarCatalogos]);
  useEffect(() => { cargar(); }, [cargar]);

  /* ── Cascade recinto → zona → ubicación / acceso ─────────────────── */
  const set = (k: keyof typeof FORM_VACIO, v: string | number) =>
    setForm(f => ({ ...f, [k]: v }));

  useEffect(() => {
    if (!form.recinto) { setZonas([]); setAccesos([]); return; }
    api.get("/api/zonas/", { params: { recinto: form.recinto } })
      .then(r => setZonas(lista(r.data))).catch(() => setZonas([]));
    api.get("/api/accesos/", { params: { recinto: form.recinto } })
      .then(r => setAccesos(lista(r.data))).catch(() => setAccesos([]));
  }, [form.recinto]);

  useEffect(() => {
    if (!form.zona_sel) { setUbicaciones([]); return; }
    api.get("/api/ubicaciones/", { params: { zona: form.zona_sel } })
      .then(r => setUbicaciones(lista(r.data))).catch(() => setUbicaciones([]));
  }, [form.zona_sel]);

  /* ── Autocomplete invitados ───────────────────────────────────────── */
  const buscarPersonas = (q: string, idx: number) => {
    setSugIdx(idx);
    setSugs([]);   // limpiar inmediatamente para no mostrar resultados de otro invitado
    clearTimeout(debRef.current);
    if (q.length < 2) return;
    debRef.current = setTimeout(() => {
      api.get("/api/citas/buscar-personas/", { params: { q } })
        .then(r => setSugs(r.data)).catch(() => setSugs([]));
    }, 280);
  };

  const seleccionarPersona = (p: Persona) => {
    if (sugIdx === null) return;
    setInvitados(inv => inv.map((it, i) =>
      i === sugIdx
        ? { nombre: p.nombre, email: p.email, telefono: p.telefono, persona_id: p.id, tipo: p.tipo }
        : it
    ));
    setSugs([]); setQuery(""); setSugIdx(null);
  };

  /* ── Abrir detalle ────────────────────────────────────────────────── */
  const abrirDetalle = (id: number) => {
    setDetalle(null); setModal("detalle"); setDetLoading(true);
    api.get(`/api/citas/${id}/`)
      .then(r => setDetalle(r.data))
      .finally(() => setDetLoading(false));
  };

  /* ── Cambiar estado ───────────────────────────────────────────────── */
  const cambiarEstado = (id: number, estado: string) =>
    api.patch(`/api/citas/${id}/`, { estado }).then(cargar);

  /* ── Eliminar ─────────────────────────────────────────────────────── */
  const eliminar = (id: number) => {
    if (!window.confirm("¿Eliminar esta cita? No se puede deshacer.")) return;
    api.delete(`/api/citas/${id}/`)
      .then(cargar)
      .catch((e: { response?: { data?: { detail?: string } } }) => {
        alert(e.response?.data?.detail ?? "No se puede eliminar la cita.");
      });
  };

  /* ── Crear cita ───────────────────────────────────────────────────── */
  const crear = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      const body: Record<string, unknown> = {
        nombre:           form.nombre,
        detalles:         form.detalles || null,
        fecha:            form.fecha,
        hora_inicio:      form.hora_inicio || null,
        hora_fin:         form.hora_fin    || null,
        tipo:             1,   // siempre Directa
        tipo_cita:        form.tipo_cita,
        estado:           form.estado,
        recinto:          Number(form.recinto),
        ubicacion:        form.ubicacion  ? Number(form.ubicacion)  : null,
        acceso:           form.acceso     ? Number(form.acceso)     : null,
        protocolo:        form.protocolo  ? Number(form.protocolo)  : null,
        asignado_a:       form.asignado_a ? Number(form.asignado_a) : null,
        asistentes_input: invitados.filter(i => i.nombre.trim()),
      };
      await api.post("/api/citas/", body);
      cerrarModal(); cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error al crear la cita."));
    } finally {
      setSaving(false);
    }
  };

  /* ── Walk-in: abre el formulario completo con tipo_cita=walk_in ──── */
  const crearWalkIn = () => {
    const hoy = new Date().toISOString().split("T")[0];
    setForm({ ...FORM_VACIO, tipo_cita: "walk_in", estado: "confirmada", fecha: hoy });
    setInvitados([{ ...INVITADO_VACIO }]);
    setError(""); setModal("crear");
  };

  /* ── Abrir editar ────────────────────────────────────────────────── */
  const abrirEditar = async (id: number) => {
    setError(""); setModal("editar"); setDetLoading(true);
    try {
      const r = await api.get(`/api/citas/${id}/`);
      const d: CitaDetalle = r.data;
      const zona_sel = d.ubicacion_zona_id ? String(d.ubicacion_zona_id) : "";
      const recintoId = d.recinto ? String(d.recinto) : "";

      // Pre-load cascade data so selects have options when the form opens
      const [zonasR, accesosR, ubicR] = await Promise.allSettled([
        recintoId ? api.get("/api/zonas/", { params: { recinto: recintoId } }) : Promise.resolve({ data: [] }),
        recintoId ? api.get("/api/accesos/", { params: { recinto: recintoId } }) : Promise.resolve({ data: [] }),
        zona_sel  ? api.get("/api/ubicaciones/", { params: { zona: zona_sel } }) : Promise.resolve({ data: [] }),
      ]);
      if (zonasR.status  === "fulfilled") setZonas(lista(zonasR.value.data));
      if (accesosR.status === "fulfilled") setAccesos(lista(accesosR.value.data));
      if (ubicR.status   === "fulfilled") setUbicaciones(lista(ubicR.value.data));

      setCitaEditId(d.id);
      setForm({
        nombre:      d.nombre     ?? "",
        detalles:    d.detalles   ?? "",
        fecha:       d.fecha      ?? "",
        hora_inicio: d.hora_inicio ? d.hora_inicio.slice(0, 5) : "",
        hora_fin:    d.hora_fin    ? d.hora_fin.slice(0, 5)    : "",
        tipo_cita:   d.tipo_cita,
        estado:      d.estado,
        recinto:     recintoId,
        zona_sel,
        ubicacion:   d.ubicacion  ? String(d.ubicacion)  : "",
        acceso:      d.acceso     ? String(d.acceso)     : "",
        protocolo:   d.protocolo  ? String(d.protocolo)  : "",
        asignado_a:  d.asignado_a ? String(d.asignado_a) : "",
      });
    } catch {
      setModal(null);
    } finally {
      setDetLoading(false);
    }
  };

  /* ── Editar cita ─────────────────────────────────────────────────── */
  const editar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!citaEditId) return;
    setSaving(true); setError("");
    try {
      await api.patch(`/api/citas/${citaEditId}/`, {
        nombre:     form.nombre,
        detalles:   form.detalles  || null,
        fecha:      form.fecha,
        hora_inicio: form.hora_inicio || null,
        hora_fin:    form.hora_fin    || null,
        tipo_cita:   form.tipo_cita,
        estado:      form.estado,
        recinto:     Number(form.recinto),
        ubicacion:   form.ubicacion  ? Number(form.ubicacion)  : null,
        acceso:      form.acceso     ? Number(form.acceso)     : null,
        protocolo:   form.protocolo  ? Number(form.protocolo)  : null,
        asignado_a:  form.asignado_a ? Number(form.asignado_a) : null,
      });
      cerrarModal(); cargar();
    } catch (err: unknown) {
      const e = err as { response?: { data?: unknown } };
      setError(JSON.stringify(e.response?.data ?? "Error al editar la cita."));
    } finally {
      setSaving(false);
    }
  };

  /* ── Cerrar modal ─────────────────────────────────────────────────── */
  const cerrarModal = () => {
    setModal(null); setForm(FORM_VACIO); setInvitados([{ ...INVITADO_VACIO }]);
    setError(""); setSugs([]); setQuery(""); setSugIdx(null);
    setCitaEditId(null);
  };

  /* ── Reenviar invitación ──────────────────────────────────────────── */
  const reenviarInvitacion = async (id: number) => {
    setReenviando(id);
    setReenviandoMsg(null);
    try {
      const res = await api.post(`/api/citas/${id}/reenviar-invitacion/`);
      const detail: string = (res.data as { detail?: string }).detail ?? "Invitaciones reenviadas.";
      setReenviandoMsg({ id, tipo: "ok", texto: detail });
      setTimeout(() => setReenviandoMsg(m => m?.id === id ? null : m), 4000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      const texto = e.response?.data?.detail ?? "Error al reenviar la invitación.";
      setReenviandoMsg({ id, tipo: "err", texto });
      setTimeout(() => setReenviandoMsg(m => m?.id === id ? null : m), 5000);
    } finally {
      setReenviando(null);
    }
  };

  /* ── Refrescar detalle abierto (tras alta/baja de asistentes) ─────── */
  const refrescarDetalle = async (id: number) => {
    const r = await api.get(`/api/citas/${id}/`);
    setDetalle(r.data);
    cargar(); // actualiza el total de asistentes en la lista
  };

  /* ── Agregar invitados a una cita existente ───────────────────────── */
  const agregarInvitados = async () => {
    if (!detalle) return;
    const asistentes = invitados.filter(i => i.nombre.trim());
    if (asistentes.length === 0) { setAgregarMsg("Escribe al menos un invitado."); return; }
    setAgregando(true); setAgregarMsg("");
    try {
      const res = await api.post(`/api/citas/${detalle.id}/agregar-asistentes/`, { asistentes });
      const n = (res.data as { agregados?: number }).agregados ?? asistentes.length;
      setInvitados([{ ...INVITADO_VACIO }]);
      await refrescarDetalle(detalle.id);
      setAgregarMsg(`${n} invitado(s) agregado(s). Se les envió la invitación.`);
      setTimeout(() => setAgregarMsg(""), 4000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setAgregarMsg(e.response?.data?.detail ?? "No se pudieron agregar los invitados.");
    } finally {
      setAgregando(false);
    }
  };

  /* ── Dar de baja / reactivar un asistente (baja lógica) ───────────── */
  const darDeBajaAsistente = async (a: Asistente) => {
    if (!detalle) return;
    if (!window.confirm(`¿Dar de baja a ${a.nombre}? Su gafete quedará sin validez en el acceso.`)) return;
    setAsistBusy(a.id);
    try {
      await api.delete(`/api/asistentes/${a.id}/`);
      await refrescarDetalle(detalle.id);
    } catch {
      alert("No se pudo dar de baja al invitado.");
    } finally {
      setAsistBusy(null);
    }
  };

  const reactivarAsistente = async (a: Asistente) => {
    if (!detalle) return;
    setAsistBusy(a.id);
    try {
      await api.patch(`/api/asistentes/${a.id}/`, { estado: 0 });
      await refrescarDetalle(detalle.id);
    } catch {
      alert("No se pudo reactivar al invitado.");
    } finally {
      setAsistBusy(null);
    }
  };

  /* ── Filas de invitados con autocomplete (reusadas en crear y detalle) ── */
  const invitadoRows = () => (
    <>
      {invitados.map((inv, idx) => (
        <div key={idx} className="col-span-2 rounded-xl border border-slate-200 p-3 relative">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Invitado {idx + 1}</span>
            {invitados.length > 1 && (
              <button type="button" onClick={() => setInvitados(is => is.filter((_, i) => i !== idx))}
                className="text-xs text-red-400 hover:text-red-600">Quitar</button>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="relative col-span-2">
              <div className="mb-1 flex items-center gap-1.5">
                <label className="text-xs font-semibold text-slate-600">Nombre *</label>
                <Ayuda>Nombre del invitado. Al escribir se buscan empleados y contactos ya registrados; selecciónalo para vincularlo y reusar sus datos.</Ayuda>
              </div>
              <input required value={inv.nombre}
                onChange={e => {
                  const v = e.target.value;
                  setInvitados(is => is.map((it, i) => i === idx ? { ...it, nombre: v, persona_id: null } : it));
                  buscarPersonas(v, idx);
                }}
                onBlur={() => setTimeout(() => { if (sugIdx === idx) setSugs([]); }, 200)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                placeholder="Buscar empleado o contacto…" />
              {sugs.length > 0 && sugIdx === idx && (
                <ul className="absolute z-20 left-0 right-0 mt-1 rounded-lg border border-slate-200 bg-white shadow-lg max-h-40 overflow-y-auto">
                  {sugs.map((s, si) => (
                    <li key={si}>
                      <button type="button" onMouseDown={() => seleccionarPersona(s)}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-blue-50">
                        <span className="font-medium text-slate-800">{s.nombre}</span>
                        {s.empresa && <span className="ml-1 text-xs text-slate-400">({s.empresa})</span>}
                        <span className="ml-1 text-xs text-slate-400">{s.email}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <div className="mb-1 flex items-center gap-1.5">
                <label className="text-xs font-semibold text-slate-600">Email</label>
                <Ayuda>Correo del invitado. A esta dirección se le envía la invitación con su gafete QR.</Ayuda>
              </div>
              <input type="email" value={inv.email}
                onChange={e => setInvitados(is => is.map((it, i) => i === idx ? { ...it, email: e.target.value } : it))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                placeholder="email@empresa.com" />
            </div>
            <div>
              <div className="mb-1 flex items-center gap-1.5">
                <label className="text-xs font-semibold text-slate-600">Teléfono</label>
                <Ayuda>Teléfono del invitado (opcional). 10 dígitos, sin lada. Ej. 5512345678</Ayuda>
              </div>
              <input type="tel" value={inv.telefono}
                onChange={e => setInvitados(is => is.map((it, i) => i === idx ? { ...it, telefono: e.target.value.replace(/\D/g, "").slice(0, 10) } : it))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                placeholder="5512345678" maxLength={10} inputMode="numeric" />
            </div>
          </div>
        </div>
      ))}
      <div className="col-span-2">
        <button type="button"
          onClick={() => setInvitados(is => [...is, { ...INVITADO_VACIO }])}
          className="flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Agregar invitado
        </button>
      </div>
    </>
  );

  /* ══════════════════════════════════════════════════════════════════
     Render
  ══════════════════════════════════════════════════════════════════ */
  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
          <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Citas</h1>
          <p className="text-xs text-slate-500">Agenda de visitas y accesos programados</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={filtroEstado} onChange={e => setFiltroEstado(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 outline-none focus:border-blue-400">
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendiente</option>
            <option value="confirmada">Confirmada</option>
            <option value="cancelada">Cancelada</option>
          </select>
          <select value={filtroTipo} onChange={e => setFiltroTipo(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 outline-none focus:border-blue-400">
            <option value="">Todos los tipos</option>
            <option value="0">Proveedor</option>
            <option value="1">Directa</option>
          </select>
          <button onClick={crearWalkIn}
            className="flex items-center gap-1.5 rounded-lg border border-violet-300 px-3 py-2 text-sm font-semibold text-violet-700 hover:bg-violet-50">
            Walk-in
          </button>
          <button onClick={() => { setError(""); setForm(FORM_VACIO); setInvitados([{ ...INVITADO_VACIO }]); setModal("crear"); }}
            className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white"
            style={{ backgroundColor: SIGNAL }}>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
            Nueva cita
          </button>
        </div>
      </div>

      {/* ── Tabla ───────────────────────────────────────────────── */}
      <div className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50 text-left">
                {["Nombre / motivo", "Fecha", "Horario", "Tipo", "Estado", "Recinto", "Asistentes", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {loading && (
                <tr><td colSpan={8} className="px-4 py-10">
                  <div className="space-y-2">{[1,2,3].map(i =>
                    <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />)}</div>
                </td></tr>
              )}
              {!loading && citas.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-sm text-slate-400">
                  Sin citas registradas.
                </td></tr>
              )}
              {!loading && citas.map(c => {
                const badge = ESTADO_BADGE[c.estado] ?? { bg: "bg-slate-100", text: "text-slate-600" };
                const tipoBadge = TIPO_CITA_BADGE[c.tipo_cita] ?? { bg: "bg-slate-100", text: "text-slate-600" };
                return (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="font-semibold" style={{ color: INK }}>{c.nombre || `Cita #${c.id}`}</p>
                      <p className="text-xs text-slate-400">{TIPO_LABEL[c.tipo] ?? "—"}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">
                      {fmtFecha(c.fecha)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
                      {c.hora_inicio && c.hora_fin
                        ? `${fmtHora(c.hora_inicio)} – ${fmtHora(c.hora_fin)}`
                        : c.hora_inicio ? fmtHora(c.hora_inicio) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${tipoBadge.bg} ${tipoBadge.text}`}>
                        {TIPO_CITA_LABEL[c.tipo_cita] ?? c.tipo_cita}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.bg} ${badge.text}`}>
                        {c.estado}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">{c.recinto_nombre || "—"}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex h-6 min-w-[1.5rem] items-center justify-center rounded-full bg-slate-100 px-1.5 text-xs font-semibold text-slate-600">
                        {c.total_asistentes}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 justify-end">
                        <button onClick={() => abrirDetalle(c.id)}
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50">
                          Ver
                        </button>
                        <button onClick={() => abrirEditar(c.id)}
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700">
                          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                          </svg>
                        </button>
                        {c.estado === "pendiente" && (
                          <button onClick={() => cambiarEstado(c.id, "confirmada")}
                            className="rounded-lg px-2 py-1 text-xs font-semibold text-white bg-green-600 hover:bg-green-700">
                            Confirmar
                          </button>
                        )}
                        {c.estado !== "cancelada" && (
                          <button onClick={() => cambiarEstado(c.id, "cancelada")}
                            className="rounded-lg border border-red-300 px-2 py-1 text-xs font-semibold text-red-600 hover:bg-red-50">
                            Cancelar
                          </button>
                        )}
                        {c.tipo_cita !== "walk_in" && (
                          <div className="flex flex-col items-end gap-0.5">
                            <button
                              onClick={() => reenviarInvitacion(c.id)}
                              disabled={reenviando === c.id}
                              title="Reenviar invitación"
                              className={`rounded-lg border px-2 py-1 text-xs font-semibold transition disabled:opacity-50 ${
                                reenviandoMsg?.id === c.id && reenviandoMsg.tipo === "ok"
                                  ? "border-green-300 bg-green-50 text-green-700"
                                  : reenviandoMsg?.id === c.id && reenviandoMsg.tipo === "err"
                                  ? "border-red-300 bg-red-50 text-red-600"
                                  : "border-slate-200 text-slate-500 hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50"
                              }`}>
                              {reenviando === c.id ? "…" : (
                                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                                  <polyline points="22,6 12,13 2,6"/>
                                </svg>
                              )}
                            </button>
                            {reenviandoMsg?.id === c.id && (
                              <span className={`text-[10px] font-semibold ${reenviandoMsg.tipo === "ok" ? "text-green-600" : "text-red-500"}`}>
                                {reenviandoMsg.tipo === "ok" ? "✓ Enviado" : "✗ Error"}
                              </span>
                            )}
                          </div>
                        )}
                        <button onClick={() => eliminar(c.id)}
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-400 hover:text-red-500 hover:border-red-200">
                          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          Modal: NUEVA CITA
      ══════════════════════════════════════════════════════════════ */}
      {modal === "crear" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          <form onSubmit={crear}
            className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">

            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold" style={{ color: INK }}>
                  {form.tipo_cita === "walk_in" ? "Registro walk-in" : "Nueva cita"}
                </h2>
                <p className="text-xs text-slate-400">
                  {form.tipo_cita === "walk_in"
                    ? "El acceso se registra al guardar — no se envían notificaciones."
                    : "Los campos marcados * son obligatorios."}
                </p>
              </div>
              <button type="button" onClick={cerrarModal}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
              </button>
            </div>

            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}

            {/* ── Sección principal ────────────────────────────────── */}
            <Section label="General">
              <Field label="Nombre / motivo *" span={2}>
                <Input required value={form.nombre} onChange={v => set("nombre", v)}
                  placeholder="Reunión mensual proveedores…" />
              </Field>

              <Field label="Tipo de cita">
                <Select value={form.tipo_cita} onChange={v => set("tipo_cita", v)}>
                  <option value="programada">Programada</option>
                  <option value="walk_in">Walk-in</option>
                  <option value="emergencia">Emergencia</option>
                </Select>
              </Field>

              <Field label="Fecha *">
                <Input required type="date" value={form.fecha} onChange={v => set("fecha", v)} />
              </Field>

              <Field label="Hora inicio">
                <Input type="time" value={form.hora_inicio} onChange={v => set("hora_inicio", v)} />
              </Field>

              <Field label="Hora fin">
                <Input type="time" value={form.hora_fin} onChange={v => set("hora_fin", v)} />
              </Field>

              <Field label="Asignado a">
                <Select value={form.asignado_a} onChange={v => set("asignado_a", v)}>
                  <option value="">Sin asignar</option>
                  {usuarios.map(u => <option key={u.id} value={u.id}>{u.nombre}</option>)}
                </Select>
              </Field>

              <Field label="Detalles" span={2}>
                <textarea value={form.detalles} onChange={e => set("detalles", e.target.value)} rows={2}
                  className="w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  placeholder="Observaciones opcionales…" />
              </Field>
            </Section>

            {/* ── Ubicación ────────────────────────────────────────── */}
            <Section label="Ubicación">
              <Field label="Recinto *">
                <Select required value={form.recinto}
                  onChange={v => setForm(f => ({ ...f, recinto: v, zona_sel: "", ubicacion: "", acceso: "" }))}>
                  <option value="">Seleccionar…</option>
                  {recintos.map(r => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                </Select>
              </Field>

              <Field label="Zona">
                <Select value={form.zona_sel}
                  onChange={v => setForm(f => ({ ...f, zona_sel: v, ubicacion: "" }))}
                  disabled={!form.recinto}>
                  <option value="">Seleccionar…</option>
                  {zonas.map(z => <option key={z.id} value={z.id}>{z.nombre}</option>)}
                </Select>
              </Field>

              <Field label="Ubicación">
                <Select value={form.ubicacion} onChange={v => set("ubicacion", v)} disabled={!form.zona_sel}>
                  <option value="">Seleccionar…</option>
                  {ubicaciones.map(u => <option key={u.id} value={u.id}>{u.nombre}</option>)}
                </Select>
              </Field>

              <Field label="Punto de acceso">
                <Select value={form.acceso} onChange={v => set("acceso", v)} disabled={!form.recinto}>
                  <option value="">Seleccionar…</option>
                  {accesos.map(a => <option key={a.id} value={a.id}>{a.nombre}</option>)}
                </Select>
              </Field>

              <Field label="Protocolo">
                <Select value={form.protocolo} onChange={v => set("protocolo", v)}>
                  <option value="">Sin protocolo</option>
                  {protocolos.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </Select>
              </Field>
            </Section>

            {/* ── Invitados ────────────────────────────────────────── */}
            <Section label="Invitados">
              {invitadoRows()}
            </Section>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={cerrarModal}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: SIGNAL }}>
                {saving ? "Creando…" : "Crear cita"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          Modal: DETALLE
      ══════════════════════════════════════════════════════════════ */}
      {modal === "detalle" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6"
          onClick={e => { if (e.target === e.currentTarget) cerrarModal(); }}>
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-bold" style={{ color: INK }}>Detalle de cita</h2>
              <button onClick={cerrarModal}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
              </button>
            </div>

            {detLoading && <div className="py-10 text-center text-slate-400">Cargando…</div>}
            {detalle && !detLoading && (
              <>
                {/* Info principal */}
                <div className="mb-4 rounded-xl border border-slate-100 p-4">
                  <div className="mb-3 flex flex-wrap items-start gap-2">
                    <h3 className="flex-1 text-sm font-bold" style={{ color: INK }}>
                      {detalle.nombre || `Cita #${detalle.id}`}
                    </h3>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${ESTADO_BADGE[detalle.estado]?.bg ?? "bg-slate-100"} ${ESTADO_BADGE[detalle.estado]?.text ?? "text-slate-600"}`}>
                      {detalle.estado}
                    </span>
                  </div>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                    <DL k="Fecha" v={fmtFecha(detalle.fecha)} />
                    <DL k="Horario"
                      v={detalle.hora_inicio ? `${fmtHora(detalle.hora_inicio)}${detalle.hora_fin ? ` – ${fmtHora(detalle.hora_fin)}` : ""}` : "—"} />
                    <DL k="Tipo" v={TIPO_LABEL[detalle.tipo]} />
                    <DL k="Tipo cita" v={TIPO_CITA_LABEL[detalle.tipo_cita] ?? detalle.tipo_cita} />
                    <DL k="Recinto" v={detalle.recinto_nombre ?? "—"} />
                    <DL k="Ubicación" v={detalle.ubicacion_nombre ?? "—"} />
                    <DL k="Punto de acceso" v={detalle.acceso_nombre ?? "—"} />
                    <DL k="Protocolo" v={detalle.protocolo_nombre ?? "—"} />
                    {detalle.tipo === 0 && <>
                      <DL k="Proveedor" v={detalle.proveedor_nombre ?? "—"} />
                      <DL k="Límite" v={detalle.limite != null ? String(detalle.limite) : "—"} />
                    </>}
                    <DL k="Asignado a" v={detalle.asignado_a_nombre ?? "—"} />
                    {detalle.detalles && <div className="col-span-2">
                      <dt className="font-semibold text-slate-400">Detalles</dt>
                      <dd className="text-slate-600 leading-relaxed">{detalle.detalles}</dd>
                    </div>}
                  </dl>
                </div>

                {/* Asistentes */}
                {detalle.asistentes.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Invitados ({detalle.asistentes.length})
                    </h4>
                    <div className="space-y-2">
                      {detalle.asistentes.map(a => (
                        <div key={a.id}
                          className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                          <div>
                            <p className="text-sm font-semibold" style={{ color: INK }}>{a.nombre}</p>
                            <p className="text-xs text-slate-400">
                              {a.email || "—"}{a.telefono ? ` · ${a.telefono}` : ""}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold
                              ${a.estado === 1 ? "bg-green-100 text-green-700" : a.estado === 2 ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-700"}`}>
                              {ASISTENTE_ESTADO[a.estado] ?? "—"}
                            </span>
                            {a.ine_capturado && (
                              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                                INE ✓
                              </span>
                            )}
                            {detalle.tipo_cita !== "walk_in" && (
                              a.estado === 2 ? (
                                <button onClick={() => reactivarAsistente(a)} disabled={asistBusy === a.id}
                                  className="text-[11px] font-semibold text-blue-600 hover:text-blue-700 disabled:opacity-50">
                                  {asistBusy === a.id ? "…" : "Reactivar"}
                                </button>
                              ) : (
                                <button onClick={() => darDeBajaAsistente(a)} disabled={asistBusy === a.id}
                                  className="text-[11px] font-semibold text-red-500 hover:text-red-600 disabled:opacity-50">
                                  {asistBusy === a.id ? "…" : "Dar de baja"}
                                </button>
                              )
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {detalle.asistentes.length === 0 && (
                  <p className="text-center text-xs text-slate-400 py-4">Sin invitados registrados.</p>
                )}

                {/* Agregar invitados (a una cita existente) */}
                {detalle.tipo_cita !== "walk_in" && detalle.estado !== "cancelada" && (
                  <div className="mt-4 rounded-xl border border-slate-100 p-4">
                    <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Agregar invitados
                    </h4>
                    <div className="grid grid-cols-2 gap-3">
                      {invitadoRows()}
                    </div>
                    {agregarMsg && <p className="mt-2 text-xs text-slate-500">{agregarMsg}</p>}
                    <div className="mt-3 flex justify-end">
                      <button onClick={agregarInvitados} disabled={agregando}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50">
                        {agregando ? "Agregando…" : "Agregar y enviar invitación"}
                      </button>
                    </div>
                  </div>
                )}

                {/* Reenviar invitación */}
                {detalle.tipo_cita !== "walk_in" && (
                  <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold text-slate-600">Reenviar invitación</p>
                        <p className="text-[11px] text-slate-400">
                          Envía el correo con el gafete QR a todos los asistentes con email.
                        </p>
                      </div>
                      <button
                        onClick={() => reenviarInvitacion(detalle.id)}
                        disabled={reenviando === detalle.id}
                        className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50">
                        {reenviando === detalle.id ? "Enviando…" : (
                          <>
                            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                              <polyline points="22,6 12,13 2,6"/>
                            </svg>
                            Reenviar
                          </>
                        )}
                      </button>
                    </div>
                    {reenviandoMsg?.id === detalle.id && (
                      <p className={`mt-2 text-xs font-semibold ${reenviandoMsg.tipo === "ok" ? "text-green-600" : "text-red-500"}`}>
                        {reenviandoMsg.tipo === "ok" ? "✓" : "✗"} {reenviandoMsg.texto}
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          Modal: EDITAR CITA
      ══════════════════════════════════════════════════════════════ */}
      {modal === "editar" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          {detLoading ? (
            <div className="rounded-2xl bg-white p-10 shadow-2xl text-sm text-slate-400">Cargando…</div>
          ) : (
            <form onSubmit={editar}
              className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">

              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold" style={{ color: INK }}>Editar cita</h2>
                  <p className="text-xs text-slate-400">Los campos marcados * son obligatorios.</p>
                </div>
                <button type="button" onClick={cerrarModal}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
                </button>
              </div>

              {error && (
                <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
              )}

              <Section label="General">
                <Field label="Nombre / motivo *" span={2}>
                  <Input required value={form.nombre} onChange={v => set("nombre", v)}
                    placeholder="Reunión mensual proveedores…" />
                </Field>

                <Field label="Tipo de cita">
                  <Select value={form.tipo_cita} onChange={v => set("tipo_cita", v)}>
                    <option value="programada">Programada</option>
                    <option value="walk_in">Walk-in</option>
                    <option value="emergencia">Emergencia</option>
                  </Select>
                </Field>

                <Field label="Estado">
                  <Select value={form.estado} onChange={v => set("estado", v)}>
                    <option value="pendiente">Pendiente</option>
                    <option value="confirmada">Confirmada</option>
                    <option value="cancelada">Cancelada</option>
                  </Select>
                </Field>

                <Field label="Fecha *">
                  <Input required type="date" value={form.fecha} onChange={v => set("fecha", v)} />
                </Field>

                <Field label="Hora inicio">
                  <Input type="time" value={form.hora_inicio} onChange={v => set("hora_inicio", v)} />
                </Field>

                <Field label="Hora fin">
                  <Input type="time" value={form.hora_fin} onChange={v => set("hora_fin", v)} />
                </Field>

                <Field label="Asignado a">
                  <Select value={form.asignado_a} onChange={v => set("asignado_a", v)}>
                    <option value="">Sin asignar</option>
                    {usuarios.map(u => <option key={u.id} value={u.id}>{u.nombre}</option>)}
                  </Select>
                </Field>

                <Field label="Detalles" span={2}>
                  <textarea value={form.detalles} onChange={e => set("detalles", e.target.value)} rows={2}
                    className="w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                    placeholder="Observaciones opcionales…" />
                </Field>
              </Section>

              <Section label="Ubicación">
                <Field label="Recinto *">
                  <Select required value={form.recinto}
                    onChange={v => setForm(f => ({ ...f, recinto: v, zona_sel: "", ubicacion: "", acceso: "" }))}>
                    <option value="">Seleccionar…</option>
                    {recintos.map(r => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                  </Select>
                </Field>

                <Field label="Zona">
                  <Select value={form.zona_sel}
                    onChange={v => setForm(f => ({ ...f, zona_sel: v, ubicacion: "" }))}
                    disabled={!form.recinto}>
                    <option value="">Seleccionar…</option>
                    {zonas.map(z => <option key={z.id} value={z.id}>{z.nombre}</option>)}
                  </Select>
                </Field>

                <Field label="Ubicación">
                  <Select value={form.ubicacion} onChange={v => set("ubicacion", v)} disabled={!form.zona_sel}>
                    <option value="">Seleccionar…</option>
                    {ubicaciones.map(u => <option key={u.id} value={u.id}>{u.nombre}</option>)}
                  </Select>
                </Field>

                <Field label="Punto de acceso">
                  <Select value={form.acceso} onChange={v => set("acceso", v)} disabled={!form.recinto}>
                    <option value="">Seleccionar…</option>
                    {accesos.map(a => <option key={a.id} value={a.id}>{a.nombre}</option>)}
                  </Select>
                </Field>

                <Field label="Protocolo">
                  <Select value={form.protocolo} onChange={v => set("protocolo", v)}>
                    <option value="">Sin protocolo</option>
                    {protocolos.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                  </Select>
                </Field>
              </Section>

              <div className="mt-2 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                Al guardar se reenvía la invitación actualizada a todos los invitados con correo.
              </div>

              <div className="mt-4 flex justify-end gap-2">
                <button type="button" onClick={cerrarModal}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                  Cancelar
                </button>
                <button type="submit" disabled={saving}
                  className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                  style={{ backgroundColor: SIGNAL }}>
                  {saving ? "Guardando…" : "Guardar cambios"}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Subcomponentes del formulario ──────────────────────────────────────── */
function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-4">
      <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">{label}</p>
      <div className="grid grid-cols-2 gap-3">{children}</div>
    </div>
  );
}

function Field({ label, span, help, children }: { label: string; span?: 1 | 2; help?: string; children: ReactNode }) {
  const ayuda = help ?? AYUDA_CITA[label];
  return (
    <div className={span === 2 ? "col-span-2" : ""}>
      <div className="mb-1 flex items-center gap-1.5">
        <label className="text-xs font-semibold text-slate-600">{label}</label>
        {ayuda && <Ayuda>{ayuda}</Ayuda>}
      </div>
      {children}
    </div>
  );
}

function Input({ required, type = "text", value, onChange, placeholder, disabled, min }: {
  required?: boolean; type?: string; value: string; min?: string;
  onChange: (v: string) => void; placeholder?: string; disabled?: boolean;
}) {
  return (
    <input required={required} type={type} value={value} disabled={disabled} min={min}
      onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 disabled:bg-slate-50 disabled:text-slate-400" />
  );
}

function Select({ required, value, onChange, disabled, children }: {
  required?: boolean; value: string | number; onChange: (v: string) => void;
  disabled?: boolean; children: ReactNode;
}) {
  return (
    <select required={required} value={value} disabled={disabled} onChange={e => onChange(e.target.value)}
      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 disabled:bg-slate-50 disabled:text-slate-400">
      {children}
    </select>
  );
}

function DL({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="font-semibold text-slate-400">{k}</dt>
      <dd className="text-slate-700">{v}</dd>
    </div>
  );
}
