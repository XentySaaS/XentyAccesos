import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

interface Proveedor {
  id: number;
  nombre: string;
  razon_social: string | null;
  rfc: string | null;
  email: string | null;
  email_responsable: string | null;
  nombre_responsable: string | null;
  telefono: string | null;
  estado: string;
  creado?: string;
}

interface Revision {
  empresa: {
    nombre: string;
    razon_social: string | null;
    rfc: string | null;
    repse: boolean;
    sua: boolean;
  };
  responsable: {
    nombre: string | null;
    email: string | null;
    puesto: string | null;
    curp: string | null;
    nss: string | null;
    ine: boolean;
    foto: boolean;
  };
  estado: string;
}

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const ESTADO_META: Record<string, { bg: string; text: string; label: string }> = {
  pendiente:  { bg: "bg-amber-100",  text: "text-amber-800",  label: "Pendiente"  },
  confirmado: { bg: "bg-blue-100",   text: "text-blue-800",   label: "Confirmado" },
  activo:     { bg: "bg-green-100",  text: "text-green-800",  label: "Activo"     },
  inactivo:   { bg: "bg-slate-100",  text: "text-slate-500",  label: "Inactivo"   },
};

function EstadoBadge({ estado }: { estado: string }) {
  const m = ESTADO_META[estado] ?? { bg: "bg-slate-100", text: "text-slate-500", label: estado };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${m.bg} ${m.text}`}>
      {m.label}
    </span>
  );
}

const FORM_INIT = {
  nombre: "", razon_social: "", rfc: "",
  email_responsable: "", nombre_responsable: "", telefono: "",
};

export default function Proveedores() {
  const [items,    setItems]    = useState<Proveedor[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [modal,    setModal]    = useState<"crear" | "editar" | null>(null);
  const [editId,   setEditId]   = useState<number | null>(null);
  const [form,     setForm]     = useState(FORM_INIT);
  const [saving,   setSaving]   = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  // acciones por fila
  const [invitando,  setInvitando]  = useState<number | null>(null);
  const [activando,  setActivando]  = useState<number | null>(null);
  const [tokenModal, setTokenModal] = useState<{ url: string; nombre: string; emailEnviado: boolean } | null>(null);

  // revisión de documentos del onboarding
  const [revisar,    setRevisar]    = useState<Proveedor | null>(null);
  const [revData,    setRevData]    = useState<Revision | null>(null);
  const [revLoading, setRevLoading] = useState(false);

  async function cargar() {
    setLoading(true);
    try {
      const { data } = await api.get("/api/proveedores/");
      setItems(Array.isArray(data) ? data : data.results ?? []);
    } finally { setLoading(false); }
  }
  useEffect(() => { cargar(); }, []);

  const set = (k: keyof typeof FORM_INIT, v: string) => setForm(f => ({ ...f, [k]: v }));

  function abrirEditar(p: Proveedor) {
    setForm({
      nombre: p.nombre, razon_social: p.razon_social ?? "", rfc: p.rfc ?? "",
      email_responsable: p.email_responsable ?? "", nombre_responsable: p.nombre_responsable ?? "",
      telefono: p.telefono ?? "",
    });
    setEditId(p.id); setError(null); setModal("editar");
  }

  async function eliminar(p: Proveedor) {
    if (!confirm(`¿Eliminar al proveedor "${p.nombre}"? Esta acción no se puede deshacer.`)) return;
    setError(null);
    try {
      await api.delete(`/api/proveedores/${p.id}/`);
      await cargar();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "No se pudo eliminar el proveedor.");
    }
  }

  async function guardar(e: FormEvent) {
    e.preventDefault(); setSaving(true); setError(null);
    const payload = {
      nombre:             form.nombre,
      razon_social:       form.razon_social || null,
      rfc:                form.rfc.toUpperCase().trim(),
      email_responsable:  form.email_responsable.toLowerCase().trim(),
      nombre_responsable: form.nombre_responsable || null,
      telefono:           form.telefono || null,
    };
    try {
      if (modal === "editar" && editId) {
        await api.patch(`/api/proveedores/${editId}/`, payload);
        setModal(null); setForm(FORM_INIT); setEditId(null); await cargar();
      } else {
        const { data } = await api.post<Proveedor>("/api/proveedores/", payload);
        setModal(null); setForm(FORM_INIT); await cargar();
        if (form.email_responsable) {
          setTokenModal({ url: "", nombre: data.nombre, emailEnviado: true });
        }
      }
    } catch (err: any) {
      const d = err?.response?.data;
      setError(d?.detail ?? d?.rfc?.[0] ?? d?.email_responsable?.[0] ?? "No se pudo guardar.");
    } finally { setSaving(false); }
  }

  async function invitar(p: Proveedor) {
    setInvitando(p.id); setError(null);
    try {
      const { data } = await api.post(`/api/proveedores/${p.id}/invitar/`);
      // Armamos el link desde el origen del admin (mismo subdominio de tenant y mismo puerto) para
      // que Nginx preserve el Host y django-tenants resuelva el tenant; así se evita el 404
      // "No tenant for hostname" que daba al apuntar a un host sin contexto de tenant (localhost:5175).
      const onboardingUrl = `${window.location.origin}/proveedores/onboarding?token=${data.token}`;
      setTokenModal({ url: onboardingUrl, nombre: p.nombre, emailEnviado: data.email_enviado });
      await cargar();
    } catch {
      setError("No se pudo generar la invitación.");
    } finally { setInvitando(null); }
  }

  async function abrirRevision(p: Proveedor) {
    setRevisar(p); setRevData(null); setRevLoading(true); setError(null);
    try {
      const { data } = await api.get<Revision>(`/api/proveedores/${p.id}/revision/`);
      setRevData(data);
    } catch {
      setError("No se pudieron cargar los documentos del proveedor.");
      setRevisar(null);
    } finally { setRevLoading(false); }
  }

  async function activar(p: Proveedor) {
    setActivando(p.id); setError(null);
    try {
      await api.post(`/api/proveedores/${p.id}/activar/`);
      setRevisar(null); setRevData(null);
      await cargar();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "No se pudo activar.");
    } finally { setActivando(null); }
  }

  const F = form;

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ backgroundColor: "#EFF6FF" }}>
          <svg className="h-5 w-5" style={{ color: SIGNAL }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M20 7H4a2 2 0 00-2 2v6a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z"/>
            <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Proveedores</h1>
          <p className="text-xs text-slate-500">
            Alta, onboarding por correo y activación de empresas proveedoras
          </p>
        </div>
        <button onClick={() => { setError(null); setForm(FORM_INIT); setModal("crear"); }}
          className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: SIGNAL }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Nuevo proveedor
        </button>
      </div>

      {/* Flujo de estados */}
      <div className="mb-4 flex items-center gap-2 rounded-lg border border-slate-100 bg-white px-4 py-3 text-xs text-slate-500 shadow-sm">
        <span className="font-semibold text-amber-700">Pendiente</span>
        <span>→ envía invitación por correo →</span>
        <span className="font-semibold text-blue-700">Confirmado</span>
        <span>→ revisa documentos y activa →</span>
        <span className="font-semibold text-green-700">Activo</span>
        <span>→ se notifica al proveedor con el link al panel</span>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button className="ml-3 text-xs underline" onClick={() => setError(null)}>Cerrar</button>
        </div>
      )}

      {/* Tabla */}
      <div className="overflow-hidden rounded-card bg-white shadow-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left">
              {["Empresa", "RFC", "Responsable", "Teléfono", "Estado", "Acciones"].map(h => (
                <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading && (
              <tr><td colSpan={6} className="px-4 py-8">
                <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-5 animate-pulse rounded bg-slate-100" />)}</div>
              </td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-400">
                Sin proveedores registrados.
              </td></tr>
            )}
            {!loading && items.map(p => (
              <tr key={p.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <p className="font-semibold" style={{ color: INK }}>{p.nombre}</p>
                  {p.razon_social && p.razon_social !== p.nombre && (
                    <p className="text-xs text-slate-400">{p.razon_social}</p>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">{p.rfc ?? "—"}</td>
                <td className="px-4 py-3">
                  {p.nombre_responsable
                    ? <p className="text-sm font-medium" style={{ color: INK }}>{p.nombre_responsable}</p>
                    : <span className="text-slate-400">—</span>
                  }
                  {p.email_responsable && (
                    <p className="text-xs text-slate-400">{p.email_responsable}</p>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-500">{p.telefono ?? "—"}</td>
                <td className="px-4 py-3"><EstadoBadge estado={p.estado} /></td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1.5">
                    {/* Invitar: pendiente o confirmado sin responsable */}
                    {(p.estado === "pendiente") && (
                      <button
                        onClick={() => invitar(p)}
                        disabled={invitando === p.id}
                        className="rounded-lg border border-blue-200 px-3 py-1 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 disabled:opacity-50">
                        {invitando === p.id ? "Enviando…" : "✉ Invitar"}
                      </button>
                    )}
                    {/* Editar y eliminar: solo en pendiente (aún sin cuenta ni datos del proveedor) */}
                    {p.estado === "pendiente" && (
                      <button
                        onClick={() => abrirEditar(p)}
                        className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50">
                        ✎ Editar
                      </button>
                    )}
                    {p.estado === "pendiente" && (
                      <button
                        onClick={() => eliminar(p)}
                        className="rounded-lg border border-red-100 px-3 py-1 text-xs font-medium text-red-500 transition hover:bg-red-50">
                        ✕ Eliminar
                      </button>
                    )}
                    {/* Re-invitar: confirmado pero sin activar todavía */}
                    {p.estado === "confirmado" && (
                      <button
                        onClick={() => invitar(p)}
                        disabled={invitando === p.id}
                        className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50">
                        {invitando === p.id ? "…" : "Re-invitar"}
                      </button>
                    )}
                    {/* Revisar y activar: el admin valida documentos antes de activar */}
                    {p.estado === "confirmado" && (
                      <button
                        onClick={() => abrirRevision(p)}
                        className="rounded-lg px-3 py-1 text-xs font-semibold text-white transition hover:opacity-90"
                        style={{ backgroundColor: "#16A34A" }}>
                        Revisar y activar
                      </button>
                    )}
                    {/* Revisar: ver documentos de un proveedor ya activo */}
                    {p.estado === "activo" && (
                      <button
                        onClick={() => abrirRevision(p)}
                        className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50">
                        Revisar
                      </button>
                    )}
                    {/* Desactivar: solo activos */}
                    {p.estado === "activo" && (
                      <button
                        onClick={async () => {
                          if (!confirm(`¿Desactivar a ${p.nombre}?`)) return;
                          await api.post(`/api/proveedores/${p.id}/desactivar/`);
                          await cargar();
                        }}
                        className="rounded-lg border border-red-100 px-3 py-1 text-xs font-medium text-red-500 transition hover:bg-red-50">
                        Desactivar
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Modal crear / editar proveedor ────────────────────── */}
      {(modal === "crear" || modal === "editar") && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={guardar} className="w-full max-w-lg rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>
              {modal === "editar" ? "Editar proveedor" : "Nuevo proveedor"}
            </h2>
            <p className="mb-4 text-xs text-slate-400">
              {modal === "editar"
                ? "Actualiza los datos del proveedor. El RFC se valida contra la lista 69-B del SAT."
                : "El RFC se valida contra la lista 69-B del SAT. Al enviar la invitación, el responsable recibirá un correo con el link de registro (válido 72 horas)."}
            </p>

            {error && (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}

            <div className="space-y-3">
              {/* Datos empresa */}
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Empresa</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="prov-nombre" className="text-xs font-semibold text-slate-600">Nombre de la empresa *</label>
                    <Ayuda>Nombre comercial de la empresa proveedora. Aparece en invitaciones a eventos, gafetes y la bitácora.</Ayuda>
                  </div>
                  <input id="prov-nombre" required value={F.nombre} onChange={e => set("nombre", e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="prov-razon" className="text-xs font-semibold text-slate-600">Razón social</label>
                    <Ayuda>Nombre legal completo de la empresa, tal como aparece en su constancia fiscal (puede diferir del nombre comercial).</Ayuda>
                  </div>
                  <input id="prov-razon" value={F.razon_social} onChange={e => set("razon_social", e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="prov-rfc" className="text-xs font-semibold text-slate-600">RFC *</label>
                    <Ayuda>Registro Federal de Contribuyentes de la empresa (12-13 caracteres, p. ej. ABC010101XX9). Se valida su estructura y contra la lista 69-B del SAT antes de dar de alta.</Ayuda>
                  </div>
                  <input id="prov-rfc" required value={F.rfc} onChange={e => set("rfc", e.target.value.toUpperCase())}
                    maxLength={13} placeholder="ABC010101XXX"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono uppercase outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                </div>
              </div>

              {/* Datos responsable */}
              <p className="mt-1 text-xs font-bold uppercase tracking-wider text-slate-400">Responsable</p>
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="prov-resp" className="text-xs font-semibold text-slate-600">Nombre del responsable *</label>
                  <Ayuda>Persona de contacto de la empresa. Se le crea una cuenta de acceso al portal de proveedores para gestionar sus empleados y documentos.</Ayuda>
                </div>
                <input id="prov-resp" required value={F.nombre_responsable} onChange={e => set("nombre_responsable", e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="prov-email" className="text-xs font-semibold text-slate-600">Correo del responsable *</label>
                    <Ayuda>Correo con el que el responsable inicia sesión en el portal de proveedores. Debe ser único; ahí recibe las invitaciones a eventos.</Ayuda>
                  </div>
                  <input id="prov-email" required type="email" value={F.email_responsable} onChange={e => set("email_responsable", e.target.value)}
                    placeholder="contacto@empresa.com"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="prov-tel" className="text-xs font-semibold text-slate-600">Teléfono</label>
                    <Ayuda>Teléfono de contacto del responsable (opcional). Formato con lada, p. ej. +52 55 1234 5678.</Ayuda>
                  </div>
                  <input id="prov-tel" value={F.telefono} onChange={e => set("telefono", e.target.value)}
                    placeholder="+52 55…"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
                </div>
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => { setModal(null); setEditId(null); }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-50"
                style={{ backgroundColor: SIGNAL }}>
                {saving ? "Guardando…" : (modal === "editar" ? "Guardar cambios" : "Crear proveedor")}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal token de invitación ─────────────────────────── */}
      {tokenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 mx-auto">
              <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
              </svg>
            </div>
            <h2 className="mb-1 text-center text-base font-bold" style={{ color: INK }}>Invitación generada</h2>
            <p className="mb-4 text-center text-sm text-slate-500">
              {tokenModal.emailEnviado
                ? <>Correo enviado a <strong>{tokenModal.nombre}</strong>.<br/>Si necesitas compartir el link manualmente, usa "Invitar" en la tabla.</>
                : <>Comparte este link con el responsable de <strong>{tokenModal.nombre}</strong>.</>
              }
            </p>
            {tokenModal.emailEnviado && (
              <div className="mb-3 flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-xs text-green-700">
                <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M20 6L9 17l-5-5"/>
                </svg>
                Correo enviado con link de registro (válido 72 h)
              </div>
            )}
            {tokenModal.url && (
              <>
                <div
                  className="mb-2 cursor-pointer rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 font-mono text-xs break-all select-all text-slate-700 hover:bg-slate-100 transition"
                  title="Haz clic para copiar"
                  onClick={() => { navigator.clipboard.writeText(tokenModal.url); }}
                >
                  {tokenModal.url}
                </div>
                <p className="mb-4 text-center text-xs text-slate-400">
                  Haz clic para copiar · Página pública de registro (no requiere cuenta previa) · Válido 72 h
                </p>
              </>
            )}
            <button onClick={() => setTokenModal(null)}
              className="w-full rounded-lg py-2.5 text-sm font-semibold text-white"
              style={{ backgroundColor: SIGNAL }}>
              Entendido
            </button>
          </div>
        </div>
      )}

      {/* ── Modal revisión de documentos ──────────────────────── */}
      {revisar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="flex max-h-full w-full max-w-2xl flex-col rounded-modal bg-white shadow-panel">
            {/* Cabecera */}
            <div className="flex items-start justify-between border-b border-slate-100 px-6 py-4">
              <div>
                <h2 className="text-base font-bold" style={{ color: INK }}>Revisar documentos</h2>
                <p className="text-xs text-slate-500">{revisar.nombre}</p>
              </div>
              <button onClick={() => { setRevisar(null); setRevData(null); }}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>

            {/* Cuerpo */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {revLoading || !revData ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Empresa */}
                  <section>
                    <p className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-400">Empresa</p>
                    <div className="mb-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                      <Dato label="Razón social" valor={revData.empresa.razon_social} />
                      <Dato label="RFC" valor={revData.empresa.rfc} mono />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <DocVisor proveedorId={revisar.id} tipo="repse" label="REPSE" disponible={revData.empresa.repse} />
                      <DocVisor proveedorId={revisar.id} tipo="sua"   label="SUA"   disponible={revData.empresa.sua} />
                    </div>
                  </section>

                  {/* Responsable */}
                  <section>
                    <p className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-400">Responsable</p>
                    <div className="mb-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                      <Dato label="Nombre" valor={revData.responsable.nombre} />
                      <Dato label="Correo" valor={revData.responsable.email} />
                      <Dato label="Puesto" valor={revData.responsable.puesto} />
                      <Dato label="CURP" valor={revData.responsable.curp} mono />
                      <Dato label="NSS" valor={revData.responsable.nss} mono />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <DocVisor proveedorId={revisar.id} tipo="ine"  label="INE"  disponible={revData.responsable.ine} />
                      <DocVisor proveedorId={revisar.id} tipo="foto" label="Foto" disponible={revData.responsable.foto} />
                    </div>
                  </section>
                </div>
              )}
            </div>

            {/* Pie de acciones */}
            <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-6 py-4">
              <p className="text-xs text-slate-400">
                {revisar.estado === "confirmado"
                  ? "Al activar se enviará un correo al responsable con el acceso al panel."
                  : "Proveedor activo."}
              </p>
              <div className="flex gap-2">
                <button onClick={() => { setRevisar(null); setRevData(null); }}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                  Cerrar
                </button>
                {revisar.estado === "confirmado" && (
                  <button
                    onClick={() => activar(revisar)}
                    disabled={activando === revisar.id}
                    className="rounded-lg px-5 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
                    style={{ backgroundColor: "#16A34A" }}>
                    {activando === revisar.id ? "Activando…" : "✓ Aprobar y activar"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* Dato simple etiqueta/valor */
function Dato({ label, valor, mono }: { label: string; valor: string | null; mono?: boolean }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`text-sm ${valor ? "text-slate-700" : "text-slate-300"} ${mono ? "font-mono" : ""}`}>
        {valor || "—"}
      </p>
    </div>
  );
}

/* Visor de un documento: descarga el archivo con auth (blob) y previsualiza o abre. */
function DocVisor({ proveedorId, tipo, label, disponible }: {
  proveedorId: number; tipo: "repse" | "sua" | "ine" | "foto"; label: string; disponible: boolean;
}) {
  const [url, setUrl]   = useState<string | null>(null);
  const [esImg, setEsImg] = useState(false);
  const [estado, setEstado] = useState<"idle" | "cargando" | "error">("idle");

  useEffect(() => {
    if (!disponible) return;
    let revoke: string | null = null;
    setEstado("cargando");
    api.get(`/api/proveedores/${proveedorId}/documento/?tipo=${tipo}`, { responseType: "blob" })
      .then(r => {
        const blob: Blob = r.data;
        const objUrl = URL.createObjectURL(blob);
        revoke = objUrl;
        setUrl(objUrl);
        setEsImg(blob.type.startsWith("image/"));
        setEstado("idle");
      })
      .catch(() => setEstado("error"));
    return () => { if (revoke) URL.revokeObjectURL(revoke); };
  }, [proveedorId, tipo, disponible]);

  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-600">{label}</span>
        {disponible
          ? <span className="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-800">Cargado</span>
          : <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-400">Sin documento</span>}
      </div>
      {!disponible ? (
        <p className="py-3 text-center text-xs text-slate-300">No se entregó</p>
      ) : estado === "cargando" ? (
        <div className="flex justify-center py-4"><div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" /></div>
      ) : estado === "error" ? (
        <p className="py-3 text-center text-xs text-red-500">No se pudo cargar</p>
      ) : url && esImg ? (
        <a href={url} target="_blank" rel="noreferrer">
          <img src={url} alt={label} className="h-28 w-full rounded object-cover ring-1 ring-slate-100" />
        </a>
      ) : url ? (
        <a href={url} target="_blank" rel="noreferrer"
          className="flex items-center justify-center gap-1.5 rounded-lg bg-slate-50 py-3 text-xs font-medium text-blue-600 hover:bg-slate-100">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Abrir documento ↗
        </a>
      ) : null}
    </div>
  );
}
