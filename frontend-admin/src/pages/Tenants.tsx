import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

interface Tenant {
  id: number;
  schema_name: string;
  nombre: string;
  estado: string;
  plan: string | null;
  saldo: number;
  modo_solo_lectura: boolean;
}

interface Pagina {
  results?: Tenant[];
}

const COLOR: Record<string, string> = {
  trial: "bg-blue-100 text-blue-700",
  activo: "bg-emerald-100 text-emerald-700",
  suspendido: "bg-amber-100 text-amber-700",
  cancelado: "bg-red-100 text-red-700",
};

export default function Tenants() {
  const [items, setItems] = useState<Tenant[]>([]);
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();

  async function cargar() {
    const { data } = await api.get<Pagina | Tenant[]>("/api/admin/tenants/");
    setItems(Array.isArray(data) ? data : data.results ?? []);
  }

  useEffect(() => {
    cargar().catch(() => {});
  }, []);

  async function accion(t: Tenant, nombre: "suspender" | "activar" | "cancelar") {
    await api.post(`/api/admin/tenants/${t.id}/${nombre}/`);
    await cargar();
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="flex items-center border-b bg-white px-6 py-3 shadow-sm">
        <span className="font-semibold">Xenty Admin · Tenants</span>
        <button className="ml-auto rounded border px-3 py-1 text-sm"
          onClick={() => { logout(); navigate("/"); }}>Salir</button>
      </nav>
      <main className="mx-auto max-w-4xl p-6">
        <table className="w-full overflow-hidden rounded-lg bg-white shadow">
          <thead className="bg-slate-100 text-left text-sm">
            <tr>
              <th className="px-4 py-2">Empresa</th>
              <th className="px-4 py-2">Subdominio</th>
              <th className="px-4 py-2">Estado</th>
              <th className="px-4 py-2">Plan</th>
              <th className="px-4 py-2">Créditos</th>
              <th className="px-4 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} className="border-t text-sm">
                <td className="px-4 py-2">{t.nombre}</td>
                <td className="px-4 py-2 text-slate-500">{t.schema_name}</td>
                <td className="px-4 py-2">
                  <span className={`rounded px-2 py-0.5 text-xs ${COLOR[t.estado] ?? ""}`}>
                    {t.estado}
                  </span>
                </td>
                <td className="px-4 py-2">{t.plan ?? "—"}</td>
                <td className="px-4 py-2">{t.saldo}</td>
                <td className="px-4 py-2 space-x-1">
                  {t.estado !== "suspendido" && (
                    <button className="rounded border px-2 py-1 text-xs"
                      onClick={() => accion(t, "suspender")}>Suspender</button>
                  )}
                  {t.estado !== "activo" && (
                    <button className="rounded border px-2 py-1 text-xs"
                      onClick={() => accion(t, "activar")}>Activar</button>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                  Sin tenants todavía.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </main>
    </div>
  );
}
