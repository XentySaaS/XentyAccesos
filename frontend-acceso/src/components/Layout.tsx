import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../store/auth";

export default function Layout() {
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="flex items-center gap-5 border-b bg-white px-6 py-3 shadow-sm">
        <Link to="/dashboard" className="font-semibold text-slate-900">
          Xenty Acceso
        </Link>
        <Link to="/recintos" className="text-slate-600 hover:text-slate-900">
          Recintos
        </Link>
        <Link to="/proveedores" className="text-slate-600 hover:text-slate-900">
          Proveedores
        </Link>
        <button
          className="ml-auto rounded border px-3 py-1 text-sm"
          onClick={() => {
            logout();
            navigate("/");
          }}
        >
          Salir
        </button>
      </nav>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
