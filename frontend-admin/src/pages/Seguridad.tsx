import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

interface Me { email?: string; mfa_habilitado?: boolean; }
interface Enrolamiento { secret: string; otpauth_uri: string; qr: string; }

const INK = "#0F1B2D";

export default function Seguridad() {
  const [me, setMe]             = useState<Me | null>(null);
  const [enrol, setEnrol]       = useState<Enrolamiento | null>(null);
  const [codigo, setCodigo]     = useState("");
  const [msg, setMsg]           = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [cargando, setCargando] = useState<"me" | "enrolar" | "activar" | null>("me");

  async function cargarMe() {
    setCargando("me");
    try {
      const { data } = await api.get<Me>("/api/admin/me/");
      setMe(data);
    } finally {
      setCargando(null);
    }
  }

  useEffect(() => { cargarMe(); }, []);

  async function enrolar() {
    setMsg(null);
    setCargando("enrolar");
    try {
      const { data } = await api.post<Enrolamiento>("/api/admin/mfa/totp/enrolar/");
      setEnrol(data);
      setCodigo("");
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo iniciar el enrolamiento." });
    } finally {
      setCargando(null);
    }
  }

  async function activar(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setCargando("activar");
    try {
      await api.post("/api/admin/mfa/totp/activar/", { codigo });
      setEnrol(null);
      setCodigo("");
      setMsg({ tipo: "ok", texto: "MFA activado correctamente." });
      await cargarMe();
    } catch {
      setMsg({ tipo: "error", texto: "Código inválido. Intenta de nuevo." });
    } finally {
      setCargando(null);
    }
  }

  const activo = me?.mfa_habilitado === true;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Seguridad</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Autenticación en dos pasos (TOTP) de tu cuenta de super-administrador.
        </p>
      </div>

      {msg && (
        <div className={`mb-4 rounded-lg px-4 py-2.5 text-sm ring-1 ${
          msg.tipo === "ok" ? "bg-green-50 text-green-700 ring-green-100" : "bg-red-50 text-red-700 ring-red-100"
        }`}>
          {msg.texto}
        </div>
      )}

      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        {/* Estado actual */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-700">MFA por TOTP</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              {cargando === "me" ? "Cargando…" : me?.email ?? "—"}
            </p>
          </div>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            activo ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-600"
          }`}>
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: activo ? "#16A34A" : "#94A3B8" }} />
            {activo ? "Activado" : "No configurado"}
          </span>
        </div>

        {/* Acción de enrolamiento */}
        {!enrol && (
          <div className="mt-5 border-t border-slate-100 pt-5">
            <p className="text-sm text-slate-500">
              {activo
                ? "Puedes volver a configurar el segundo factor (esto reemplaza el secreto actual)."
                : "Protege el control plane exigiendo un código temporal además de tu contraseña."}
            </p>
            <button
              onClick={enrolar}
              disabled={cargando !== null}
              className="mt-3 rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {cargando === "enrolar" ? "Generando…" : activo ? "Reconfigurar MFA" : "Configurar MFA"}
            </button>
          </div>
        )}

        {/* Paso de activación */}
        {enrol && (
          <div className="mt-5 border-t border-slate-100 pt-5">
            <ol className="space-y-4 text-sm text-slate-600">
              <li>
                <span className="font-medium text-slate-700">1. Agrega la clave a tu app autenticadora</span>
                <p className="mt-1 text-xs text-slate-400">
                  Escanea este código QR con tu app (Google Authenticator, Authy, 1Password…), o
                  ingresa manualmente la clave secreta.
                </p>
                <div className="mt-3 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
                  <img
                    src={enrol.qr}
                    alt="Código QR para configurar el segundo factor"
                    className="h-40 w-40 rounded-lg bg-white p-2 ring-1 ring-slate-100"
                  />
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Clave secreta</p>
                    <code className="mt-1 block break-all rounded-lg bg-slate-50 px-3 py-2 font-mono text-sm tracking-wider text-slate-800 ring-1 ring-slate-100">
                      {enrol.secret}
                    </code>
                  </div>
                </div>
              </li>
              <li>
                <span className="font-medium text-slate-700">2. Ingresa el código de 6 dígitos que genera la app</span>
                <form onSubmit={activar} className="mt-2 flex flex-wrap items-center gap-2">
                  <input
                    type="text" required autoFocus inputMode="numeric" maxLength={6}
                    value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
                    className="w-40 rounded-lg border border-slate-200 px-3 py-2 text-center text-lg tracking-[0.3em] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    placeholder="000000"
                  />
                  <button
                    type="submit" disabled={cargando !== null || codigo.length < 6}
                    className="rounded-lg bg-[#16A34A] px-3.5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
                  >
                    {cargando === "activar" ? "Activando…" : "Activar"}
                  </button>
                  <button
                    type="button" onClick={() => { setEnrol(null); setCodigo(""); }}
                    className="text-xs text-slate-400 hover:text-slate-600"
                  >
                    Cancelar
                  </button>
                </form>
              </li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}
