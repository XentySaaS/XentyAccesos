import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

interface Me { nombre?: string; email?: string; empresa?: string; }

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: "/dashboard",  label: "Inicio" },
  { to: "/empleados",  label: "Empleados" },
  { to: "/eventos",    label: "Mis eventos" },
];

export default function Layout() {
  const logout    = useAuth((s) => s.logout);
  const navigate  = useNavigate();
  const location  = useLocation();
  const [me, setMe]               = useState<Me | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [esMobile, setEsMobile] = useState(false);

  useEffect(() => {
    api.get<Me>("/api/auth/me/").then((r) => setMe(r.data)).catch(() => {});
  }, []);

  // Viewport móvil (<768px): el sidebar es un drawer flotante, no empuja el contenido.
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const upd = () => setEsMobile(mq.matches);
    upd();
    mq.addEventListener("change", upd);
    return () => mq.removeEventListener("change", upd);
  }, []);
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  const mostrarLabels = esMobile || collapsed === false;

  function handleLogout() { logout(); navigate("/"); }

  return (
    <div className="flex h-screen overflow-hidden bg-[#F1F4F8]">
      {/* Backdrop del drawer (solo móvil) */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={() => setMobileOpen(false)} aria-hidden />
      )}

      {/* ── Sidebar (drawer flotante en móvil, fijo en escritorio) ── */}
      <aside
        style={{ backgroundColor: "#0F1B2D" }}
        className={`fixed inset-y-0 left-0 z-40 flex flex-col flex-shrink-0 transform transition-transform duration-200 md:static md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } w-60 ${collapsed ? "md:w-16" : "md:w-60"}`}
      >
        {/* Logo + toggles */}
        <div className="flex items-center justify-between px-4 py-5">
          {mostrarLabels ? (
            <img src={`${import.meta.env.BASE_URL}xenty-white.png`} alt="Xenty" className="h-6 w-auto" />
          ) : (
            <div
              className="mx-auto flex h-8 w-8 items-center justify-center rounded-full text-sm font-extrabold text-white"
              style={{ backgroundColor: "#2563EB" }}
              title="Xenty"
            >
              X
            </div>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="ml-auto hidden rounded p-1 text-slate-400 hover:text-white hover:bg-white/10 md:block"
            title={collapsed ? "Expandir" : "Colapsar"}
          >
            {collapsed ? (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
            ) : (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
            )}
          </button>
          <button
            onClick={() => setMobileOpen(false)}
            className="ml-auto rounded p-1 text-slate-400 hover:text-white hover:bg-white/10 md:hidden"
            title="Cerrar menú"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                title={!mostrarLabels ? item.label : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-[#2563EB] text-white"
                    : "text-[#CBD5E1] hover:bg-white/10 hover:text-white"
                }`}
              >
                <NavIcon label={item.label} active={active} />
                {mostrarLabels && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Footer: usuario */}
        <div style={{ borderTopColor: "#1F3147" }} className="border-t px-3 py-4">
          {me ? (
            <div className={`flex items-center gap-2 ${!mostrarLabels ? "justify-center" : ""}`}>
              <div
                style={{ backgroundColor: "#2563EB" }}
                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white uppercase"
              >
                {(me.nombre ?? me.email ?? "?")[0]}
              </div>
              {mostrarLabels && (
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-white">{me.nombre ?? "Proveedor"}</p>
                  <p className="truncate text-[11px] text-slate-400">{me.empresa ?? me.email ?? "Autoservicio"}</p>
                </div>
              )}
              {mostrarLabels && (
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
            <button
              onClick={handleLogout}
              className={`flex w-full items-center gap-2 rounded p-1 text-slate-400 hover:text-white hover:bg-white/10 ${!mostrarLabels ? "justify-center" : ""}`}
              title="Cerrar sesión"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
              {mostrarLabels && <span className="text-xs">Cerrar sesión</span>}
            </button>
          )}
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 py-0 h-14">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded p-2 text-slate-600 hover:bg-slate-100 md:hidden"
            title="Abrir menú" aria-label="Abrir menú"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
          </button>
          <div className="flex items-center gap-4">
            <span className="tabular text-sm text-slate-500"><Clock /></span>
          </div>
        </header>

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
    "Inicio":     <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
    "Empleados":  <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>,
    "Documentos": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
    "Mis eventos":<svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
  };
  return icons[label] ?? <span className={`h-4 w-4 ${cls}`} />;
}
