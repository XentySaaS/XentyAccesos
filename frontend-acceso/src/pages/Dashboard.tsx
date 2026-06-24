import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

export default function Dashboard() {
  const [me, setMe] = useState<Record<string, unknown> | null>(null);
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/api/auth/me/").then((r) => setMe(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen p-8">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Xenty Acceso</h1>
        <button className="rounded border px-3 py-1"
          onClick={() => { logout(); navigate("/"); }}>Salir</button>
      </header>
      <pre className="rounded bg-slate-100 p-4 text-sm">{JSON.stringify(me, null, 2)}</pre>
    </div>
  );
}
