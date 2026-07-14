import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

interface Recinto { id: number; nombre: string; }

interface Usuario {
  id: number;
  email: string;
  nombre: string;
  rol: string;
  activo: boolean;
  recinto: number | null;
  recinto_nombre: string | null;
  telefono: string | null;
  email_verificado: string | null;
  mfa_habilitado: boolean;
  creado: string;
}

interface PermisoModulo {
  modulo: string;
  modulo_display: string;
  ver: boolean;
  crear: boolean;
  editar: boolean;
  eliminar: boolean;
}

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const ROLES = [
  { value: "administrador", label: "Administrador" },
  { value: "gerente",       label: "Gerente"       },
  { value: "editor",        label: "Editor"        },
  { value: "guardia",       label: "Guardia"       },
  { value: "recepcion",     label: "Recepcionista" },
  { value: "verificador",   label: "Verificador"   },
  { value: "usuario",       label: "Usuario"       },
];

const ROL_BADGE: Record<string, { bg: string; text: string }> = {
  administrador: { bg: "bg-purple-100", text: "text-purple-800" },
  gerente:       { bg: "bg-blue-100",   text: "text-blue-800"   },
  editor:        { bg: "bg-cyan-100",   text: "text-cyan-800"   },
  guardia:       { bg: "bg-orange-100", text: "text-orange-800" },
  recepcion:     { bg: "bg-green-100",  text: "text-green-800"  },
  verificador:   { bg: "bg-yellow-100", text: "text-yellow-800" },
  usuario:       { bg: "bg-slate-100",  text: "text-slate-600"  },
};

function rolBadge(rol: string) {
  const b = ROL_BADGE[rol] ?? ROL_BADGE.usuario;
  const label = ROLES.find(r => r.value === rol)?.label ?? rol;
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${b.bg} ${b.text}`}>
      {label}
    </span>
  );
}

type Modal = "crear" | "editar" | "permisos" | null;

export default function Usuarios() {
  const [items,    setItems]    = useState<Usuario[]>([]);
  const [recintos, setRecintos] = useState<Recinto[]>([]);
  const [error,    setError]    = useState<string | null>(null);
  const [modal,    setModal]    = useState<Modal>(null);
  const [target,   setTarget]   = useState<Usuario | null>(null);
  const [passModal, setPassModal] = useState<{ pass: string; email: string } | null>(null);

  // Crear form
  const [email,    setEmail]    = useState("");
  const [nombre,   setNombre]   = useState("");
  const [rol,      setRol]      = useState("editor");
  const [recinto,  setRecinto]  = useState("");
  const [telefono, setTelefono] = useState("");

  // Editar form
  const [eNombre,   setENombre]   = useState("");
  const [eRol,      setERol]      = useState("");
  const [eRecinto,  setERecinto]  = useState("");
  const [eTelefono, setETelefono] = useState("");
  const [eActivo,   setEActivo]   = useState(true);

  // Permisos
  const [permisos,     setPermisos]     = useState<PermisoModulo[]>([]);
  const [guardandoPerm, setGuardandoPerm] = useState(false);

  async function cargar() {
    const [u, r] = await Promise.all([
      api.get<{ results?: Usuario[] } | Usuario[]>("/api/usuarios/"),
      api.get<{ results?: Recinto[] } | Recinto[]>("/api/recintos/"),
    ]);
    setItems(Array.isArray(u.data) ? u.data : u.data.results ?? []);
    setRecintos(Array.isArray(r.data) ? r.data : r.data.results ?? []);
  }

  useEffect(() => { cargar().catch(() => setError("No se pudo cargar la lista.")); }, []);

  function abrirCrear() {
    setEmail(""); setNombre(""); setRol("editor"); setRecinto(""); setTelefono("");
    setModal("crear");
  }

  function abrirEditar(u: Usuario) {
    setENombre(u.nombre); setERol(u.rol);
    setERecinto(u.recinto ? String(u.recinto) : "");
    setETelefono(u.telefono ?? ""); setEActivo(u.activo);
    setTarget(u); setModal("editar");
  }

  async function abrirPermisos(u: Usuario) {
    setTarget(u);
    try {
      const { data } = await api.get<PermisoModulo[]>(`/api/usuarios/${u.id}/permisos/`);
      setPermisos(data);
      setModal("permisos");
    } catch (err: any) {
      const status = err?.response?.status ?? "?";
      const detail = err?.response?.data?.detail ?? err?.message ?? "";
      setError(`Error ${status} al cargar permisos${detail ? `: ${detail}` : "."}`);
    }
  }

  function cerrar() { setModal(null); setTarget(null); setError(null); }

  async function crear(e: FormEvent) {
    e.preventDefault(); setError(null);
    try {
      const { data } = await api.post<Usuario & { password_temporal?: string }>("/api/usuarios/", {
        email, nombre, rol,
        recinto: recinto || null,
        telefono: telefono || null,
      });
      if (data.password_temporal) {
        setPassModal({ pass: data.password_temporal, email: data.email });
      }
      cerrar(); await cargar();
    } catch (err: any) {
      const msg = err?.response?.data?.email?.[0]
        ?? err?.response?.data?.detail
        ?? "No se pudo crear el usuario.";
      setError(msg);
    }
  }

  async function editar(e: FormEvent) {
    e.preventDefault(); if (!target) return; setError(null);
    try {
      await api.patch(`/api/usuarios/${target.id}/`, {
        nombre: eNombre, rol: eRol,
        recinto: eRecinto || null,
        telefono: eTelefono || null,
        activo: eActivo,
      });
      cerrar(); await cargar();
    } catch { setError("No se pudo actualizar el usuario."); }
  }

  async function guardarPermisos() {
    if (!target) return;
    setGuardandoPerm(true); setError(null);
    try {
      await api.put(`/api/usuarios/${target.id}/permisos/`, permisos);
      cerrar();
    } catch { setError("No se pudieron guardar los permisos."); }
    finally { setGuardandoPerm(false); }
  }

  function togglePerm(modulo: string, campo: keyof Omit<PermisoModulo, "modulo" | "modulo_display">) {
    setPermisos(prev => prev.map(p =>
      p.modulo === modulo ? { ...p, [campo]: !p[campo] } : p
    ));
  }

  async function resetearPassword(u: Usuario) {
    if (!confirm(`¿Resetear la contraseña de ${u.nombre}?`)) return;
    try {
      const { data } = await api.post<{ password_temporal: string }>(
        `/api/usuarios/${u.id}/resetear-password/`
      );
      setPassModal({ pass: data.password_temporal, email: u.email });
    } catch { setError("No se pudo resetear la contraseña."); }
  }

  const ACCIONES: { key: keyof Omit<PermisoModulo, "modulo" | "modulo_display">; label: string }[] = [
    { key: "ver",      label: "Ver"      },
    { key: "crear",    label: "Crear"    },
    { key: "editar",   label: "Editar"   },
    { key: "eliminar", label: "Eliminar" },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{ backgroundColor: "#EFF6FF" }}>
          <svg className="h-5 w-5" style={{ color: SIGNAL }} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
          </svg>
        </div>
        <div className="flex-1">
          <h1 className="text-[20px] font-extrabold tracking-tight" style={{ color: INK }}>Usuarios</h1>
          <p className="text-xs text-slate-500">Equipo de acceso al sistema</p>
        </div>
        <button onClick={abrirCrear}
          className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          style={{ backgroundColor: SIGNAL }}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Nuevo usuario
        </button>
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
              {["Nombre", "Correo", "Rol", "Recinto", "Estado", "Acciones"].map(h => (
                <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {items.map(u => (
              <tr key={u.id} className={`hover:bg-slate-50 ${!u.activo ? "opacity-50" : ""}`}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white flex-shrink-0"
                      style={{ backgroundColor: SIGNAL }}>
                      {u.nombre[0]?.toUpperCase() ?? "?"}
                    </div>
                    <span className="font-semibold" style={{ color: INK }}>{u.nombre}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-500">{u.email}</td>
                <td className="px-4 py-3">{rolBadge(u.rol)}</td>
                <td className="px-4 py-3 text-slate-500">{u.recinto_nombre ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${u.activo ? "bg-green-100 text-green-800" : "bg-red-100 text-red-700"}`}>
                    {u.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1.5 flex-wrap">
                    <button onClick={() => abrirEditar(u)}
                      className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">
                      Editar
                    </button>
                    {u.rol === "usuario" && (
                      <button onClick={() => abrirPermisos(u)}
                        className="rounded-lg border border-blue-200 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50">
                        Permisos
                      </button>
                    )}
                    <button onClick={() => resetearPassword(u)}
                      className="rounded-lg border border-amber-200 px-3 py-1 text-xs font-medium text-amber-700 hover:bg-amber-50">
                      Reset pass
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-400">Sin usuarios registrados.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Modal crear ─────────────────────────────────────────────────────── */}
      {modal === "crear" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={crear} className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Nuevo usuario</h2>
            <p className="mb-4 text-xs text-slate-400">Se generará una contraseña temporal que se mostrará al crear.</p>

            <div className="space-y-3">
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="usr-email" className="text-xs font-semibold text-slate-600">Correo electrónico *</label>
                  <Ayuda>Correo con el que el usuario iniciará sesión. Debe ser único; a esta dirección se envía la verificación de la cuenta.</Ayuda>
                </div>
                <input id="usr-email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="usr-nombre" className="text-xs font-semibold text-slate-600">Nombre completo *</label>
                  <Ayuda>Nombre de la persona; aparece en la bitácora de acceso y en el registro de cambios (auditoría).</Ayuda>
                </div>
                <input id="usr-nombre" required value={nombre} onChange={e => setNombre(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="usr-rol" className="text-xs font-semibold text-slate-600">Rol *</label>
                    <Ayuda>Define qué módulos ve y qué acciones puede realizar. "Guardia" opera el escáner; "Verificador" revisa documentos; "Usuario" usa permisos granulares configurables aparte.</Ayuda>
                  </div>
                  <select id="usr-rol" value={rol} onChange={e => setRol(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="usr-recinto" className="text-xs font-semibold text-slate-600">Recinto</label>
                    <Ayuda>Recinto al que se asigna el usuario. Opcional; útil cuando el operador trabaja en un solo inmueble.</Ayuda>
                  </div>
                  <select id="usr-recinto" value={recinto} onChange={e => setRecinto(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    <option value="">Sin asignar</option>
                    {recintos.map(r => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="usr-tel" className="text-xs font-semibold text-slate-600">Teléfono</label>
                  <Ayuda>Contacto del usuario (opcional). 10 dígitos, sin lada. Ej. 5512345678</Ayuda>
                </div>
                <input id="usr-tel" value={telefono} onChange={e => setTelefono(e.target.value.replace(/\D/g, "").slice(0, 10))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                  placeholder="5512345678" maxLength={10} inputMode="numeric" />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={cerrar}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit"
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white"
                style={{ backgroundColor: SIGNAL }}>
                Crear usuario
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal editar ────────────────────────────────────────────────────── */}
      {modal === "editar" && target && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={editar} className="w-full max-w-md rounded-modal bg-white p-6 shadow-panel">
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Editar usuario</h2>
            <p className="mb-4 text-xs text-slate-400">{target.email}</p>

            <div className="space-y-3">
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="usr-e-nombre" className="text-xs font-semibold text-slate-600">Nombre completo *</label>
                  <Ayuda>Nombre de la persona; aparece en la bitácora de acceso y en el registro de cambios (auditoría).</Ayuda>
                </div>
                <input id="usr-e-nombre" required value={eNombre} onChange={e => setENombre(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="usr-e-rol" className="text-xs font-semibold text-slate-600">Rol *</label>
                    <Ayuda>Define qué módulos ve y qué acciones puede realizar. "Guardia" opera el escáner; "Verificador" revisa documentos; "Usuario" usa permisos granulares configurables aparte.</Ayuda>
                  </div>
                  <select id="usr-e-rol" value={eRol} onChange={e => setERol(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1.5">
                    <label htmlFor="usr-e-recinto" className="text-xs font-semibold text-slate-600">Recinto</label>
                    <Ayuda>Recinto al que se asigna el usuario. Opcional; útil cuando el operador trabaja en un solo inmueble.</Ayuda>
                  </div>
                  <select id="usr-e-recinto" value={eRecinto} onChange={e => setERecinto(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100">
                    <option value="">Sin asignar</option>
                    {recintos.map(r => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center gap-1.5">
                  <label htmlFor="usr-e-tel" className="text-xs font-semibold text-slate-600">Teléfono</label>
                  <Ayuda>Contacto del usuario (opcional). 10 dígitos, sin lada. Ej. 5512345678</Ayuda>
                </div>
                <input id="usr-e-tel" value={eTelefono} onChange={e => setETelefono(e.target.value.replace(/\D/g, "").slice(0, 10))}
                  placeholder="5512345678" maxLength={10} inputMode="numeric"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100" />
              </div>

              <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
                <div>
                  <div className="flex items-center gap-1.5">
                    <p className="text-sm font-semibold" style={{ color: INK }}>Usuario activo</p>
                    <Ayuda>Al desactivar se da de baja lógica al usuario: no podrá iniciar sesión, pero su historial se conserva (no se borra físicamente).</Ayuda>
                  </div>
                  <p className="text-xs text-slate-400">Desactivar da de baja lógica al usuario.</p>
                </div>
                <button type="button" onClick={() => setEActivo(!eActivo)}
                  className="relative h-6 w-11 rounded-full transition-colors focus:outline-none"
                  style={{ backgroundColor: eActivo ? "#2563EB" : "#CBD5E1" }}>
                  <span
                    className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform"
                    style={{ transform: eActivo ? "translateX(20px)" : "translateX(0)" }}
                  />
                </button>
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={cerrar}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="submit"
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white"
                style={{ backgroundColor: SIGNAL }}>
                Guardar cambios
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal permisos personalizados ───────────────────────────────────── */}
      {modal === "permisos" && target && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-xl rounded-modal bg-white p-6 shadow-panel">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-base font-bold" style={{ color: INK }}>Permisos personalizados</h2>
                <p className="text-xs text-slate-400 mt-0.5">{target.nombre} · {target.email}</p>
              </div>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-500">
                Rol: Usuario
              </span>
            </div>

            <p className="mb-4 rounded-lg bg-blue-50 border border-blue-100 px-3 py-2 text-xs text-blue-700">
              Activa los módulos y acciones que este usuario podrá realizar. Solo aplica al rol <strong>Usuario</strong>.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="py-2 pr-4 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Módulo</th>
                    {ACCIONES.map(a => (
                      <th key={a.key} className="py-2 px-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-400">{a.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {permisos.map(p => (
                    <tr key={p.modulo} className="hover:bg-slate-50">
                      <td className="py-2.5 pr-4 font-medium" style={{ color: INK }}>{p.modulo_display}</td>
                      {ACCIONES.map(a => (
                        <td key={a.key} className="py-2.5 px-3 text-center">
                          <input
                            type="checkbox"
                            checked={p[a.key]}
                            onChange={() => togglePerm(p.modulo, a.key)}
                            className="h-4 w-4 cursor-pointer rounded border-slate-300 accent-blue-600"
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={cerrar}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button onClick={guardarPermisos} disabled={guardandoPerm}
                className="rounded-lg px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
                style={{ backgroundColor: SIGNAL }}>
                {guardandoPerm ? "Guardando..." : "Guardar permisos"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal contraseña temporal ────────────────────────────────────────── */}
      {passModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-sm rounded-modal bg-white p-6 shadow-panel text-center">
            <div className="mb-3 mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-100">
              <svg className="h-6 w-6 text-amber-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0110 0v4"/>
              </svg>
            </div>
            <h2 className="mb-1 text-base font-bold" style={{ color: INK }}>Contraseña temporal</h2>
            <p className="mb-4 text-sm text-slate-500">
              Copia y comparte con <strong>{passModal.email}</strong>.<br />
              No se volverá a mostrar.
            </p>
            <div className="mb-5 rounded-lg bg-slate-100 px-4 py-3 font-mono text-xl tracking-widest select-all" style={{ color: INK }}>
              {passModal.pass}
            </div>
            <button onClick={() => setPassModal(null)}
              className="w-full rounded-lg py-2.5 text-sm font-semibold text-white"
              style={{ backgroundColor: SIGNAL }}>
              Entendido, ya la copié
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
