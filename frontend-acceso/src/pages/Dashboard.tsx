import { useEffect, useState } from "react";
import api from "../api/client";

interface Me {
  email?: string;
  nombre?: string;
  rol?: string;
}

export default function Dashboard() {
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    api.get<Me>("/api/auth/me/").then((r) => setMe(r.data)).catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold">Panel</h1>
      <div className="rounded-lg bg-white p-6 shadow">
        <p className="text-slate-600">Sesión iniciada como:</p>
        <p className="text-lg font-medium">{me?.nombre ?? "…"}</p>
        <p className="text-sm text-slate-500">{me?.email}</p>
        {me?.rol && <p className="mt-1 text-sm">Rol: {me.rol}</p>}
      </div>
    </div>
  );
}
