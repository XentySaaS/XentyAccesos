import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

interface Me { nombre?: string; email?: string; rol?: string; }

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/tenants", label: "Tenants" },
  { to: "/seguridad", label: "Seguridad" },
];

export default function Layout() {
  const logout    = useAuth((s) => s.logout);
  const navigate  = useNavigate();
  const location  = useLocation();
  const [me, setMe]               = useState<Me | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    api.get<Me>("/api/admin/me/").then((r) => setMe(r.data)).catch(() => {});
  }, []);

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
              <img src={`${import.meta.env.BASE_URL}xenty-white.png`} alt="Xenty" className="h-6 w-auto" />
            </div>
          )}
          {collapsed && (
            <img src={`${import.meta.env.BASE_URL}xenty-white.png`} alt="Xenty" className="mx-auto h-5 w-auto" />
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
          {NAV_ITEMS.map((item) => {
            const active =
              location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
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
              </Link>
            );
          })}
        </nav>

        {/* Footer: usuario */}
        <div style={{ borderTopColor: "#1F3147" }} className="border-t px-3 py-4">
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
                  <p className="truncate text-xs font-semibold text-white">{me.nombre ?? "Super-admin"}</p>
                  <p className="truncate text-[11px] text-slate-400">{me.email ?? "Control plane"}</p>
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
            <button
              onClick={handleLogout}
              className={`flex w-full items-center gap-2 rounded p-1 text-slate-400 hover:text-white hover:bg-white/10 ${collapsed ? "justify-center" : ""}`}
              title="Cerrar sesión"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
              {!collapsed && <span className="text-xs">Cerrar sesión</span>}
            </button>
          )}
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-0 h-14">
          <div />
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
    "Dashboard": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>,
    "Tenants": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M3 21h18"/><path d="M5 21V7l8-4v18"/><path d="M19 21V11l-6-4"/><line x1="9" y1="9" x2="9" y2="9"/><line x1="9" y1="13" x2="9" y2="13"/></svg>,
    "Seguridad": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  };
  return icons[label] ?? <span className={`h-4 w-4 ${cls}`} />;
}
