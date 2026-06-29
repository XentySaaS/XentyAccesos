import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

interface Me { nombre?: string; email?: string; rol?: string; }

/* Navegación gateada por rol según spec */
const NAV_ITEMS: { to: string; label: string; roles?: string[]; badge?: string }[] = [
  { to: "/dashboard",   label: "Inicio" },
  { to: "/eventos",     label: "Eventos" },
  { to: "/citas",       label: "Citas" },
  { to: "/proveedores", label: "Proveedores" },
  { to: "/verificacion",label: "Verificación", roles: ["administrador","gerente","verificador","editor"] },
  { to: "/escaner",     label: "Escáner",      roles: ["guardia","administrador","recepcion"] },
  { to: "/recintos",    label: "Recintos",     roles: ["administrador","gerente"] },
  { to: "/sanciones",   label: "Sanciones",    roles: ["administrador","gerente","editor"] },
  { to: "/mensajeria",  label: "Mensajería",   roles: ["administrador","gerente"] },
  { to: "/usuarios",    label: "Usuarios",     roles: ["administrador"] },
  { to: "/catalogos",   label: "Catálogos",    roles: ["administrador"] },
  { to: "/historial",   label: "Historial",    roles: ["administrador"] },
];

const ROL_LABEL: Record<string, string> = {
  administrador: "Administrador",
  gerente:       "Gerente",
  editor:        "Editor",
  guardia:       "Guardia",
  recepcion:     "Recepcionista",
  verificador:   "Verificador",
  usuario:       "Usuario",
};

export default function Layout() {
  const logout    = useAuth((s) => s.logout);
  const navigate  = useNavigate();
  const location  = useLocation();
  const [me, setMe]         = useState<Me | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    api.get<Me>("/api/auth/me/").then((r) => setMe(r.data)).catch(() => {});
  }, []);

  const rol = me?.rol ?? "";
  const visibles = NAV_ITEMS.filter((n) => !n.roles || n.roles.includes(rol));

  function handleLogout() { logout(); navigate("/"); }

  return (
    <div className="flex h-screen overflow-hidden bg-[#F1F4F8]">
      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside
        style={{ backgroundColor: "#0F1B2D" }}
        className={`flex flex-col flex-shrink-0 transition-all duration-200 ${collapsed ? "w-16" : "w-60"}`}
      >
        {/* Logo + colapsar */}
        <div className="flex items-center justify-between px-4 py-5">
          {!collapsed && (
            <div className="flex items-center gap-2">
              {/* Logo placeholder: cuadro signal-600 con cruz */}
              <span
                style={{ backgroundColor: "#2563EB" }}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded text-white font-bold text-sm"
              >
                +
              </span>
              <span className="text-white font-semibold text-sm tracking-tight">Xenty Acceso</span>
            </div>
          )}
          {collapsed && (
            <span
              style={{ backgroundColor: "#2563EB" }}
              className="mx-auto flex h-7 w-7 items-center justify-center rounded text-white font-bold text-sm"
            >
              +
            </span>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="ml-auto rounded p-1 text-slate-400 hover:text-white hover:bg-white/10"
            title={collapsed ? "Expandir" : "Colapsar"}
          >
            {collapsed ? (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
            ) : (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
            )}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
          {visibles.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                title={collapsed ? item.label : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-[#2563EB] text-white"
                    : "text-[#CBD5E1] hover:bg-white/10 hover:text-white"
                }`}
              >
                <NavIcon label={item.label} active={active} />
                {!collapsed && <span>{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className="ml-auto rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer: usuario */}
        <div
          style={{ borderTopColor: "#1F3147" }}
          className="border-t px-3 py-4"
        >
          {me ? (
            <div className={`flex items-center gap-2 ${collapsed ? "justify-center" : ""}`}>
              <div
                style={{ backgroundColor: "#2563EB" }}
                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white uppercase"
              >
                {(me.nombre ?? me.email ?? "?")[0]}
              </div>
              {!collapsed && (
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-white">{me.nombre}</p>
                  <p className="truncate text-[11px] text-slate-400">{ROL_LABEL[me.rol ?? ""] ?? me.rol}</p>
                </div>
              )}
              {!collapsed && (
                <button
                  onClick={handleLogout}
                  className="ml-1 rounded p-1 text-slate-400 hover:text-white hover:bg-white/10"
                  title="Cerrar sesión"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                  </svg>
                </button>
              )}
            </div>
          ) : (
            !collapsed && <div className="h-8 animate-pulse rounded bg-white/10" />
          )}
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-0 h-14">
          <div />
          <div className="flex items-center gap-4">
            <span className="tabular text-sm text-slate-500">
              <Clock />
            </span>
          </div>
        </header>

        {/* Contenido */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

/* Reloj en vivo */
function Clock() {
  const [t, setT] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setT(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return <>{t.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}</>;
}

/* Iconos por sección (lucide inline simplificado) */
function NavIcon({ label, active }: { label: string; active: boolean }) {
  const cls = `h-4 w-4 flex-shrink-0 ${active ? "text-white" : "text-slate-400"}`;
  const icons: Record<string, JSX.Element> = {
    "Inicio":       <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
    "Eventos":      <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
    "Citas":        <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
    "Proveedores":  <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>,
    "Empleados":    <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
    "Verificación": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>,
    "Escáner":      <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="3" width="5" height="5"/><rect x="16" y="3" width="5" height="5"/><rect x="3" y="16" width="5" height="5"/><path d="M21 16h-3v3"/><path d="M18 21h3"/><path d="M21 19v-3"/><path d="M13 3v5h5"/><path d="M13 13h5v5"/><path d="M13 8v5"/><path d="M8 13H3"/></svg>,
    "Recintos":     <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>,
    "Sanciones":    <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
    "Mensajería":   <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>,
    "Usuarios":     <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>,
    "Catálogos":    <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M4 6h16M4 10h16M4 14h16M4 18h16"/></svg>,
    "Historial":    <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>,
  };
  return icons[label] ?? <span className={`h-4 w-4 ${cls}`} />;
}
