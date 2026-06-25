import { FormEvent, useState } from "react";
import api from "../api/client";

interface Resultado {
  permitido: boolean;
  motivo: string;
  tipo_acceso: string | null;
}

export default function Escaner() {
  const [qr, setQr] = useState("");
  const [res, setRes] = useState<Resultado | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function escanear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setRes(null);
    try {
      const { data } = await api.post<Resultado>("/api/acceso/escanear/", { qr });
      setRes(data);
    } catch {
      setError("No autorizado (requiere rol guardia o administrador).");
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold">Escáner de acceso</h1>
      <p className="text-sm text-slate-500">
        Pega el contenido del QR del gafete. El sistema valida firma, pertenencia, vigencia,
        documentos y sanciones, y registra el acceso.
      </p>

      <form onSubmit={escanear} className="space-y-3 rounded-lg bg-white p-4 shadow">
        <textarea className="w-full rounded border px-3 py-2 font-mono text-xs" rows={4}
          placeholder="Contenido del QR…" value={qr} onChange={(e) => setQr(e.target.value)} required />
        <button className="rounded bg-slate-900 px-4 py-2 text-white" type="submit">Validar acceso</button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>

      {res && (
        <div className={`rounded-lg p-5 text-center shadow ${res.permitido ? "bg-emerald-50" : "bg-red-50"}`}>
          <p className={`text-3xl font-bold ${res.permitido ? "text-emerald-700" : "text-red-700"}`}>
            {res.permitido ? "ACCESO CONCEDIDO" : "ACCESO DENEGADO"}
          </p>
          <p className="mt-2 text-slate-600">{res.motivo}</p>
        </div>
      )}
    </div>
  );
}
