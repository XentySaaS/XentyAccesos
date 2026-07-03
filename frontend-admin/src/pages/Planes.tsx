import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

interface Plan {
  id: number;
  clave: string;
  nombre: string;
  descripcion: string | null;
  precio_mensual: string;        // DRF DecimalField -> string
  stripe_price_id: string | null;
  modulos: string[];
  limites: Record<string, unknown>;
  activo: boolean;
}

interface Pagina { results?: Plan[]; }

const INK = "#0F1B2D";

// Debe coincidir con TODOS_LOS_MODULOS del backend (sembrar_planes.py).
const MODULOS = [
  "recintos", "proveedores", "empleados", "documentos", "eventos", "citas",
  "acceso", "gafetes", "sanciones", "dispositivos", "mensajeria", "cumplimiento", "ocr",
];

type Borrador = {
  id?: number;
  clave: string;
  nombre: string;
  descripcion: string;
  precio_mensual: string;
  stripe_price_id: string;
  modulos: string[];
  limitesTexto: string;   // JSON editable
  activo: boolean;
};

const VACIO: Borrador = {
  clave: "", nombre: "", descripcion: "", precio_mensual: "0",
  stripe_price_id: "", modulos: [], limitesTexto: "{}", activo: true,
};

export default function Planes() {
  const [items, setItems]     = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal]     = useState<Borrador | null>(null);
  const [error, setError]     = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function cargar() {
    setLoading(true);
    const { data } = await api.get<Pagina | Plan[]>("/api/admin/planes/");
    setItems(Array.isArray(data) ? data : data.results ?? []);
    setLoading(false);
  }

  useEffect(() => { cargar().catch(() => setLoading(false)); }, []);

  function abrirNuevo() { setError(null); setModal({ ...VACIO }); }
  function abrirEditar(p: Plan) {
    setError(null);
    setModal({
      id: p.id, clave: p.clave, nombre: p.nombre, descripcion: p.descripcion ?? "",
      precio_mensual: String(p.precio_mensual), stripe_price_id: p.stripe_price_id ?? "",
      modulos: [...p.modulos], limitesTexto: JSON.stringify(p.limites ?? {}, null, 2), activo: p.activo,
    });
  }

  function toggleModulo(m: string) {
    setModal((b) => b && ({ ...b, modulos: b.modulos.includes(m) ? b.modulos.filter((x) => x !== m) : [...b.modulos, m] }));
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    if (!modal) return;
    setError(null);

    let limites: unknown;
    try {
      limites = JSON.parse(modal.limitesTexto || "{}");
    } catch {
      setError("El campo «Límites» no es JSON válido.");
      return;
    }

    const payload = {
      clave: modal.clave, nombre: modal.nombre, descripcion: modal.descripcion || null,
      precio_mensual: modal.precio_mensual || "0", stripe_price_id: modal.stripe_price_id || null,
      modulos: modal.modulos, limites, activo: modal.activo,
    };

    setGuardando(true);
    try {
      if (modal.id) await api.patch(`/api/admin/planes/${modal.id}/`, payload);
      else await api.post("/api/admin/planes/", payload);
      setModal(null);
      await cargar();
    } catch (err) {
      const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data;
      const detalle = data && (data.detail as string) ||
        (data ? Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" · ") : "");
      setError(detalle || "No se pudo guardar el plan.");
    } finally {
      setGuardando(false);
    }
  }

  async function eliminar(p: Plan) {
    if (!confirm(`¿Eliminar el plan «${p.nombre}»? Si tiene suscripciones, mejor desactívalo.`)) return;
    try {
      await api.delete(`/api/admin/planes/${p.id}/`);
      await cargar();
    } catch (err) {
      const detalle = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      alert(detalle ?? "No se pudo eliminar el plan.");
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ color: INK }}>Planes</h1>
          <p className="mt-0.5 text-sm text-slate-500">Planes comerciales: precio, módulos incluidos y límites.</p>
        </div>
        <button onClick={abrirNuevo} className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90">
          + Nuevo plan
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          </div>
        ) : items.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-400">Aún no hay planes. Crea el primero.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Plan</th>
                <th className="px-5 py-3">Clave</th>
                <th className="px-5 py-3">Precio/mes</th>
                <th className="px-5 py-3">Módulos</th>
                <th className="px-5 py-3">Estado</th>
                <th className="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50/60">
                  <td className="px-5 py-3 font-medium text-slate-800">{p.nombre}</td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-500">{p.clave}</td>
                  <td className="px-5 py-3 tabular text-slate-700">${p.precio_mensual}</td>
                  <td className="px-5 py-3 text-slate-500">{p.modulos.length} módulos</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ${p.activo ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-600"}`}>
                      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: p.activo ? "#16A34A" : "#94A3B8" }} />
                      {p.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex justify-end gap-1.5">
                      <button onClick={() => abrirEditar(p)} className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">Editar</button>
                      <button onClick={() => eliminar(p)} className="rounded-lg border border-red-200 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-50">Eliminar</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal crear/editar */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={() => setModal(null)}>
          <form
            onSubmit={guardar}
            onClick={(e) => e.stopPropagation()}
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-panel"
          >
            <h2 className="text-base font-bold" style={{ color: INK }}>{modal.id ? "Editar plan" : "Nuevo plan"}</h2>

            {error && <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-100">{error}</div>}

            <div className="mt-4 grid grid-cols-2 gap-3">
              <Campo label="Clave" ayuda="Identificador estable usado por el código (no cambiar a la ligera).">
                <input required value={modal.clave} disabled={!!modal.id}
                  onChange={(e) => setModal({ ...modal, clave: e.target.value })}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-50 disabled:text-slate-400" />
              </Campo>
              <Campo label="Nombre">
                <input required value={modal.nombre}
                  onChange={(e) => setModal({ ...modal, nombre: e.target.value })}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
              </Campo>
              <Campo label="Precio mensual (MXN)">
                <input type="number" min="0" step="0.01" value={modal.precio_mensual}
                  onChange={(e) => setModal({ ...modal, precio_mensual: e.target.value })}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
              </Campo>
              <Campo label="Stripe price ID" ayuda="ID del precio en Stripe (prod). Vacío en sandbox.">
                <input value={modal.stripe_price_id}
                  onChange={(e) => setModal({ ...modal, stripe_price_id: e.target.value })}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
              </Campo>
            </div>

            <div className="mt-3">
              <Campo label="Descripción">
                <textarea rows={2} value={modal.descripcion}
                  onChange={(e) => setModal({ ...modal, descripcion: e.target.value })}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
              </Campo>
            </div>

            <div className="mt-3">
              <p className="mb-1 block text-sm font-medium text-slate-700">Módulos incluidos</p>
              <p className="mb-2 text-xs text-slate-400">Gobiernan el acceso comercial (RequiereModulo). Sin módulos = acceso libre.</p>
              <div className="grid grid-cols-3 gap-1.5">
                {MODULOS.map((mod) => (
                  <label key={mod} className="flex items-center gap-1.5 text-xs text-slate-600">
                    <input type="checkbox" checked={modal.modulos.includes(mod)} onChange={() => toggleModulo(mod)} />
                    {mod}
                  </label>
                ))}
              </div>
            </div>

            <div className="mt-3">
              <Campo label="Límites (JSON)" ayuda='Ej: {"usuarios": 50, "eventos": 500}'>
                <textarea rows={3} value={modal.limitesTexto}
                  onChange={(e) => setModal({ ...modal, limitesTexto: e.target.value })}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
              </Campo>
            </div>

            <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={modal.activo} onChange={(e) => setModal({ ...modal, activo: e.target.checked })} />
              Plan activo (visible para nuevas suscripciones)
            </label>

            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cancelar</button>
              <button type="submit" disabled={guardando} className="rounded-lg bg-[#2563EB] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
                {guardando ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function Campo({ label, ayuda, children }: { label: string; ayuda?: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {ayuda && <span className="mt-0.5 block text-[11px] text-slate-400">{ayuda}</span>}
    </label>
  );
}
