/**
 * Calendario — módulo del sidebar (recrea la página Calendar del origen).
 * Vista de mes hecha a mano (sin librerías): eventos (rango de días, azul) y citas
 * (un día, verde) del mes visible, servidos por /api/reportes/calendario/.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

interface EventoCal {
  id: number; nombre: string; inicio: string; fin: string; estado: string;
  recinto: string | null; protocolo: string | null;
  hora_inicio: string | null; hora_fin: string | null; descripcion: string | null; proveedores: number;
}
interface CitaCal {
  id: number; nombre: string; fecha: string; estado: string; tipo_cita: string;
  recinto: string | null; proveedor: string | null;
  hora_inicio: string | null; hora_fin: string | null; detalles: string | null; asistentes: number;
}
interface Resp      { eventos: EventoCal[]; citas: CitaCal[]; }
type Detalle = { tipo: "evento"; item: EventoCal } | { tipo: "cita"; item: CitaCal };

const INK = "#0F1B2D";
const AZUL = "#2563EB";   // eventos
const VERDE = "#16A34A";  // citas
const ROJO = "#DC2626";   // cancelados (citas o eventos)

const MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
const DIAS  = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];

function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
/** Índice de columna Lun=0 … Dom=6 (getDay: Dom=0). */
function colLunes(d: Date): number { return (d.getDay() + 6) % 7; }

interface Marca { tipo: "evento" | "cita"; id: number; nombre: string; cancelado: boolean; }

export default function Calendario() {
  const navigate = useNavigate();
  const [cursor, setCursor] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [data, setData]     = useState<Resp>({ eventos: [], citas: [] });
  const [cargando, setCargando] = useState(true);
  const [detalle, setDetalle] = useState<Detalle | null>(null);

  // Celdas de la grilla: 6 semanas desde el lunes de la semana del día 1 del mes.
  const celdas = useMemo(() => {
    const primero = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const inicio = new Date(primero);
    inicio.setDate(primero.getDate() - colLunes(primero));
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(inicio);
      d.setDate(inicio.getDate() + i);
      return d;
    });
  }, [cursor]);

  const cargar = useCallback(() => {
    setCargando(true);
    const desde = ymd(celdas[0]);
    const hasta = ymd(celdas[celdas.length - 1]);
    api.get<Resp>("/api/reportes/calendario/", { params: { desde, hasta } })
      .then(r => setData(r.data))
      .catch(() => setData({ eventos: [], citas: [] }))
      .finally(() => setCargando(false));
  }, [celdas]);

  useEffect(() => { cargar(); }, [cargar]);

  // Mapa fecha(YYYY-MM-DD) → marcas del día.
  const porDia = useMemo(() => {
    const m: Record<string, Marca[]> = {};
    const push = (k: string, marca: Marca) => { (m[k] ??= []).push(marca); };
    for (const e of data.eventos) {
      const canc = e.estado === "cancelado";
      let d = new Date(e.inicio + "T00:00:00");
      const fin = new Date(e.fin + "T00:00:00");
      // Acota a la ventana visible para no iterar de más.
      let guard = 0;
      while (d <= fin && guard++ < 400) { push(ymd(d), { tipo: "evento", id: e.id, nombre: e.nombre, cancelado: canc }); d.setDate(d.getDate() + 1); }
    }
    for (const c of data.citas) {
      push(c.fecha, { tipo: "cita", id: c.id, nombre: c.nombre, cancelado: c.estado === "cancelada" });
    }
    return m;
  }, [data]);

  const hoyStr = ymd(new Date());
  const mesActual = cursor.getMonth();

  function mover(delta: number) {
    setCursor(c => new Date(c.getFullYear(), c.getMonth() + delta, 1));
  }
  function irHoy() {
    const d = new Date();
    setCursor(new Date(d.getFullYear(), d.getMonth(), 1));
  }

  function abrirMarca(marca: Marca) {
    if (marca.tipo === "evento") {
      const ev = data.eventos.find(e => e.id === marca.id);
      if (ev) setDetalle({ tipo: "evento", item: ev });
    } else {
      const c = data.citas.find(x => x.id === marca.id);
      if (c) setDetalle({ tipo: "cita", item: c });
    }
  }

  // Color del detalle: rojo si está cancelado; si no, azul (evento) / verde (cita).
  const detCancel = !!detalle && (detalle.item.estado === "cancelado" || detalle.item.estado === "cancelada");
  const detColor = detCancel ? ROJO : detalle?.tipo === "evento" ? AZUL : VERDE;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
          <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Calendario</h1>
          <p className="text-xs text-slate-500">Eventos y citas del recinto</p>
        </div>

        {/* Navegación de mes */}
        <div className="flex items-center gap-2">
          <button onClick={() => mover(-1)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <span className="min-w-[150px] text-center text-sm font-semibold" style={{ color: INK }}>
            {MESES[cursor.getMonth()]} {cursor.getFullYear()}
          </span>
          <button onClick={() => mover(1)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
          </button>
          <button onClick={irHoy} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50">Hoy</button>
        </div>
      </div>

      {/* Leyenda */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: AZUL }} /> Eventos</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: VERDE }} /> Citas</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: ROJO }} /> Canceladas</span>
        {cargando && <span className="text-slate-400">Cargando…</span>}
      </div>

      {/* Grilla del mes */}
      <div className="overflow-hidden rounded-card bg-white shadow-card">
        <div className="grid grid-cols-7 border-b border-slate-100 bg-slate-50">
          {DIAS.map(d => (
            <div key={d} className="px-2 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {celdas.map((d, i) => {
            const k = ymd(d);
            const delMes = d.getMonth() === mesActual;
            const esHoy = k === hoyStr;
            const marcas = porDia[k] ?? [];
            return (
              <div key={i}
                className={`min-h-[92px] border-b border-r border-slate-50 p-1.5 ${delMes ? "bg-white" : "bg-slate-50/40"}`}>
                <div className="mb-1 flex justify-end">
                  <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                    esHoy ? "text-white" : delMes ? "text-slate-600" : "text-slate-300"
                  }`} style={esHoy ? { backgroundColor: AZUL } : {}}>
                    {d.getDate()}
                  </span>
                </div>
                <div className="space-y-1">
                  {marcas.slice(0, 3).map((m, j) => (
                    <button key={j} onClick={() => abrirMarca(m)} title={m.nombre}
                      className="block w-full truncate rounded px-1.5 py-0.5 text-left text-[11px] font-medium text-white hover:opacity-90"
                      style={{ backgroundColor: m.cancelado ? ROJO : m.tipo === "evento" ? AZUL : VERDE, textDecoration: m.cancelado ? "line-through" : "none" }}>
                      {m.nombre}
                    </button>
                  ))}
                  {marcas.length > 3 && (
                    <span className="block px-1.5 text-[10px] text-slate-400">+{marcas.length - 3} más</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal de detalle de evento / cita */}
      {detalle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={() => setDetalle(null)}>
          <div className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel" onClick={e => e.stopPropagation()}>
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-widest"
                  style={{ color: detColor }}>
                  <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: detColor }} />
                  {detalle.tipo === "evento" ? "Evento" : "Cita"}{detCancel ? " · cancelado" : ""}
                </span>
                <h2 className="mt-0.5 text-lg font-extrabold tracking-tight" style={{ color: INK }}>{detalle.item.nombre}</h2>
              </div>
              <button onClick={() => setDetalle(null)} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <Dato k="Estado" v={detalle.item.estado} />
              <Dato k="Recinto" v={detalle.item.recinto ?? "—"} />
              {detalle.tipo === "evento" ? (
                <>
                  <Dato k="Vigencia desde" v={detalle.item.inicio} />
                  <Dato k="Vigencia hasta" v={detalle.item.fin} />
                  <Dato k="Horario" v={rango(detalle.item.hora_inicio, detalle.item.hora_fin)} />
                  <Dato k="Protocolo" v={detalle.item.protocolo ?? "—"} />
                  <Dato k="Proveedores" v={String(detalle.item.proveedores)} />
                  {detalle.item.descripcion && <Dato k="Descripción" v={detalle.item.descripcion} span />}
                </>
              ) : (
                <>
                  <Dato k="Fecha" v={detalle.item.fecha} />
                  <Dato k="Horario" v={rango(detalle.item.hora_inicio, detalle.item.hora_fin)} />
                  <Dato k="Tipo" v={detalle.item.tipo_cita} />
                  <Dato k="Proveedor" v={detalle.item.proveedor ?? "—"} />
                  <Dato k="Asistentes" v={String(detalle.item.asistentes)} />
                  {detalle.item.detalles && <Dato k="Detalles" v={detalle.item.detalles} span />}
                </>
              )}
            </dl>

            <div className="mt-5 flex justify-end">
              <button onClick={() => navigate(detalle.tipo === "evento" ? "/eventos" : "/citas")}
                className="rounded-lg px-4 py-2 text-sm font-semibold text-white"
                style={{ backgroundColor: "#2563EB" }}>
                Abrir en {detalle.tipo === "evento" ? "Eventos" : "Citas"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Dato({ k, v, span }: { k: string; v: string; span?: boolean }) {
  return (
    <div className={span ? "col-span-2" : ""}>
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{k}</dt>
      <dd className="text-slate-700">{v}</dd>
    </div>
  );
}

function rango(a: string | null, b: string | null): string {
  if (a && b) return `${a} – ${b}`;
  return a || b || "—";
}
