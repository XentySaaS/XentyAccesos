import { useRef, useState } from "react";
import api from "../api/client";

interface Sesion {
  connection_id: string;
  state: string;
  connected: boolean;
}

const inputCls =
  "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

/**
 * Gestión centralizada (super-admin) de las sesiones de WhatsApp del Connector, por tenant. El
 * navegador no conoce el secreto HMAC: el backend firma (`/api/admin/comunicaciones/sesion|qr`).
 */
export function AdminWhatsAppSesiones() {
  const [tenant, setTenant] = useState("");
  const [conn, setConn] = useState("principal");
  const [sesiones, setSesiones] = useState<Sesion[] | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const poll = useRef<ReturnType<typeof setInterval>>();

  const params = () => ({ tenant: tenant.trim(), connection_id: conn.trim() || "principal" });
  function parar() {
    if (poll.current) {
      clearInterval(poll.current);
      poll.current = undefined;
    }
  }

  async function estado(silencioso = false): Promise<Sesion[] | null> {
    if (!tenant.trim()) {
      setMsg({ tipo: "error", texto: "Escribe el tenant." });
      return null;
    }
    if (!silencioso) setBusy("estado");
    try {
      const { data } = await api.get<{ sessions: Sesion[] }>("/api/admin/comunicaciones/sesion/", {
        params: params(),
      });
      setSesiones(data.sessions || []);
      return data.sessions || [];
    } catch (e: any) {
      setMsg({ tipo: "error", texto: e?.response?.data?.detail || "No se pudo consultar." });
      return null;
    } finally {
      if (!silencioso) setBusy(null);
    }
  }

  async function verQr() {
    if (!tenant.trim()) return;
    try {
      const { data } = await api.get<{ qr?: string | null }>("/api/admin/comunicaciones/qr/", {
        params: params(),
      });
      setQr(data.qr ?? null);
    } catch {
      setQr(null);
    }
  }

  async function vincular() {
    if (!tenant.trim()) {
      setMsg({ tipo: "error", texto: "Escribe el tenant." });
      return;
    }
    setBusy("vincular");
    setMsg(null);
    setQr(null);
    parar();
    try {
      await api.post("/api/admin/comunicaciones/sesion/", params());
      setTimeout(verQr, 1500);
      poll.current = setInterval(async () => {
        const s = await estado(true);
        await verQr();
        const c = (s || []).find((x) => x.connection_id === conn.trim())?.connected;
        if (c) {
          parar();
          setQr(null);
        }
      }, 3000);
      setMsg({ tipo: "ok", texto: "Vinculación iniciada: escanea el QR." });
    } catch (e: any) {
      setMsg({ tipo: "error", texto: e?.response?.data?.detail || "No se pudo vincular." });
    } finally {
      setBusy(null);
    }
  }

  async function desvincular() {
    if (!tenant.trim()) return;
    setBusy("desvincular");
    parar();
    try {
      await api.delete("/api/admin/comunicaciones/sesion/", { params: params() });
      setQr(null);
      await estado(true);
      setMsg({ tipo: "ok", texto: "Desvinculado." });
    } catch (e: any) {
      setMsg({ tipo: "error", texto: e?.response?.data?.detail || "No se pudo desvincular." });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
      <h2 className="mb-1 text-sm font-semibold text-slate-700">Sesiones de WhatsApp por tenant</h2>
      <p className="mb-4 text-xs text-slate-400">
        Vincula, consulta o desvincula el número de WhatsApp de un tenant. Requiere el Connector
        habilitado y su URL/secreto configurados arriba.
      </p>

      {msg && (
        <div
          className={`mb-3 rounded-lg px-3 py-2 text-xs ring-1 ${
            msg.tipo === "ok"
              ? "bg-green-50 text-green-700 ring-green-100"
              : "bg-red-50 text-red-700 ring-red-100"
          }`}
        >
          {msg.texto}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Tenant (schema)</span>
          <input
            value={tenant}
            onChange={(e) => setTenant(e.target.value)}
            placeholder="museos"
            className={inputCls}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Conexión</span>
          <input
            value={conn}
            onChange={(e) => setConn(e.target.value)}
            placeholder="principal"
            className={inputCls}
          />
        </label>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => estado()}
          disabled={busy !== null}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          {busy === "estado" ? "…" : "Consultar estado"}
        </button>
        <button
          type="button"
          onClick={vincular}
          disabled={busy !== null}
          className="rounded-lg bg-[#2563EB] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy === "vincular" ? "…" : "Vincular"}
        </button>
        <button
          type="button"
          onClick={verQr}
          disabled={busy !== null || !tenant.trim()}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          Ver QR
        </button>
        <button
          type="button"
          onClick={desvincular}
          disabled={busy !== null}
          className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          {busy === "desvincular" ? "…" : "Desvincular"}
        </button>
      </div>

      {sesiones && (
        <div className="mt-3 text-sm">
          {sesiones.length === 0 ? (
            <p className="text-xs text-slate-400">Sin sesiones para este tenant.</p>
          ) : (
            <ul className="space-y-1">
              {sesiones.map((s) => (
                <li key={s.connection_id} className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${s.connected ? "bg-green-500" : "bg-slate-300"}`}
                  />
                  <span className="font-medium text-slate-700">{s.connection_id}</span>
                  <span className="text-xs text-slate-400">{s.state}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {qr && (
        <div className="mt-4 flex flex-col items-center gap-2">
          <img
            src={qr}
            alt="Código QR de WhatsApp"
            className="h-56 w-56 rounded-lg ring-1 ring-slate-200"
          />
          <p className="text-center text-xs text-slate-500">
            Escanéalo desde el teléfono del tenant (WhatsApp &gt; Dispositivos vinculados).
          </p>
        </div>
      )}
    </div>
  );
}
