import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

interface Me { nombre?: string; email?: string; rol?: string; }

/* Navegación agrupada por prioridad. El título se muestra al expandir; al colapsar es un divisor. */
const NAV_GROUPS: { title: string; items: { to: string; label: string }[] }[] = [
  {
    title: "",
    items: [{ to: "/dashboard", label: "Dashboard" }],
  },
  {
    title: "Clientes",
    items: [
      { to: "/tenants", label: "Tenants" },
      { to: "/planes", label: "Planes" },
    ],
  },
  {
    title: "Plataforma",
    items: [
      { to: "/comunicaciones", label: "Comunicaciones" },
      { to: "/seguridad", label: "Seguridad" },
    ],
  },
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
    api.get<Me>("/api/admin/me/").then((r) => setMe(r.data)).catch(() => {});
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
        <div className={`flex items-center px-3 py-4 ${mostrarLabels ? "justify-between" : "justify-center"}`}>
          {mostrarLabels && (
            <img src={`${import.meta.env.BASE_URL}xenty-white.png`} alt="Xenty" className="ml-1 h-6 w-auto" />
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="hidden rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white md:block"
            title={collapsed ? "Expandir menú" : "Colapsar menú"}
          >
            {collapsed ? (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
            ) : (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
            )}
          </button>
          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white md:hidden"
            title="Cerrar menú"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>

        {/* Nav agrupado. Scrollbar delgada y discreta. */}
        <nav className="flex-1 overflow-y-auto px-2 pb-4 [scrollbar-color:rgba(148,163,184,0.35)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-white/15 [&::-webkit-scrollbar]:w-1.5">
          {NAV_GROUPS.map((grupo, gi) => (
            <div key={grupo.title || `g${gi}`} className={gi > 0 ? "mt-4" : ""}>
              {mostrarLabels
                ? grupo.title && (
                    <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      {grupo.title}
                    </p>
                  )
                : gi > 0 && <div className="mx-auto mb-2 h-px w-8 bg-white/10" />}
              <div className="space-y-0.5">
                {grupo.items.map((item) => {
                  const active =
                    location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      title={!mostrarLabels ? item.label : undefined}
                      className={`flex items-center rounded-lg py-2 text-sm font-medium transition-colors ${
                        mostrarLabels ? "gap-3 px-3" : "justify-center px-0"
                      } ${
                        active
                          ? "bg-[#2563EB] text-white"
                          : "text-[#CBD5E1] hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      <NavIcon label={item.label} active={active} />
                      {mostrarLabels && <span className="truncate">{item.label}</span>}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
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
                  <p className="truncate text-xs font-semibold text-white">{me.nombre ?? "Super-admin"}</p>
                  <p className="truncate text-[11px] text-slate-400">{me.email ?? "Control plane"}</p>
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
    "Dashboard": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>,
    "Tenants": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M3 21h18"/><path d="M5 21V7l8-4v18"/><path d="M19 21V11l-6-4"/><line x1="9" y1="9" x2="9" y2="9"/><line x1="9" y1="13" x2="9" y2="13"/></svg>,
    "Planes": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/><path d="M8 4v16"/></svg>,
    "Seguridad": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
    "Comunicaciones": <svg className={cls} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>,
  };
  return icons[label] ?? <span className={`h-4 w-4 ${cls}`} />;
}
