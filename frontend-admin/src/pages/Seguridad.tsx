import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { registrarLlave, webauthnDisponible } from "../lib/webauthn";

interface Me {
  email?: string;
  mfa_habilitado?: boolean;
  webauthn_credenciales?: number;
  codigos_respaldo_disponibles?: number;
  codigos_respaldo_total?: number;
}
interface Enrolamiento { secret: string; otpauth_uri: string; qr: string; }

const INK = "#0F1B2D";

export default function Seguridad() {
  const [me, setMe]             = useState<Me | null>(null);
  const [enrol, setEnrol]       = useState<Enrolamiento | null>(null);
  const [codigo, setCodigo]     = useState("");
  const [nombreLlave, setNombreLlave] = useState("");
  const [msg, setMsg]           = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [cargando, setCargando] = useState<
    "me" | "enrolar" | "activar" | "desactivar" | "llave" | "respaldo" | null
  >("me");
  // Códigos de respaldo: se muestran una sola vez tras generarlos.
  const [respaldoCodigos, setRespaldoCodigos] = useState<string[] | null>(null);
  const [regenMode, setRegenMode] = useState(false);
  const [regenPass, setRegenPass] = useState("");
  const [copiado, setCopiado]     = useState(false);

  async function registrar() {
    setMsg(null);
    setCargando("llave");
    try {
      await registrarLlave(nombreLlave.trim() || "Llave de seguridad");
      setNombreLlave("");
      setMsg({ tipo: "ok", texto: "Llave registrada correctamente." });
      await cargarMe();
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo registrar la llave (cancelada o no compatible)." });
    } finally {
      setCargando(null);
    }
  }

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

  async function desactivar() {
    if (!window.confirm("¿Desactivar el MFA por TOTP? Podrás volver a configurarlo cuando quieras.")) return;
    setMsg(null);
    setCargando("desactivar");
    try {
      await api.post("/api/admin/mfa/totp/desactivar/");
      setEnrol(null);
      setMsg({ tipo: "ok", texto: "MFA por TOTP desactivado." });
      await cargarMe();
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo desactivar el MFA." });
    } finally {
      setCargando(null);
    }
  }

  async function generarRespaldo(password?: string) {
    setMsg(null);
    setCargando("respaldo");
    try {
      const { data } = await api.post<{ codigos: string[] }>(
        "/api/admin/mfa/respaldo/generar/",
        password ? { password } : {},
      );
      setRespaldoCodigos(data.codigos);
      setRegenMode(false);
      setRegenPass("");
      await cargarMe();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setMsg({ tipo: "error", texto: err?.response?.data?.detail ?? "No se pudieron generar los códigos." });
    } finally {
      setCargando(null);
    }
  }

  function descargarRespaldo() {
    if (!respaldoCodigos) return;
    const contenido =
      `Códigos de respaldo — Xenty Accesos (super-admin)\n${me?.email ?? ""}\n` +
      `Generados: ${new Date().toLocaleString("es-MX")}\n\n` +
      `${respaldoCodigos.join("\n")}\n\n` +
      "Cada código sirve UNA sola vez. Guárdalos en un lugar seguro; no se volverán a mostrar.\n";
    const url = URL.createObjectURL(new Blob([contenido], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "codigos-respaldo-xenty.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function copiarRespaldo() {
    if (!respaldoCodigos) return;
    try {
      await navigator.clipboard.writeText(respaldoCodigos.join("\n"));
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      /* clipboard bloqueado: el usuario puede descargar el .txt */
    }
  }

  const activo = me?.mfa_habilitado === true;
  const respTotal = me?.codigos_respaldo_total ?? 0;
  const respDisp = me?.codigos_respaldo_disponibles ?? 0;
  const respBadge =
    respTotal === 0
      ? "bg-slate-100 text-slate-600"
      : respDisp === 0
        ? "bg-red-100 text-red-700"
        : "bg-green-100 text-green-800";

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Seguridad</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Autenticación en dos pasos de tu cuenta de super-administrador: código TOTP, llave de
          seguridad o códigos de respaldo.
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
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={enrolar}
                disabled={cargando !== null}
                className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {cargando === "enrolar" ? "Generando…" : activo ? "Reconfigurar MFA" : "Configurar MFA"}
              </button>
              {activo && (
                <button
                  onClick={desactivar}
                  disabled={cargando !== null}
                  className="rounded-lg border border-red-200 px-3.5 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  {cargando === "desactivar" ? "Desactivando…" : "Desactivar"}
                </button>
              )}
            </div>
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

      {/* WebAuthn / llaves de seguridad */}
      <div className="mt-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-700">Llaves de seguridad (WebAuthn)</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              Passkeys o llaves físicas (FIDO2) como segundo factor, además del código TOTP.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
            {me?.webauthn_credenciales ?? 0} registrada(s)
          </span>
        </div>

        {webauthnDisponible() ? (
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              type="text" value={nombreLlave} maxLength={80}
              onChange={(e) => setNombreLlave(e.target.value)}
              placeholder="Nombre de la llave (ej. YubiKey, iPhone)"
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
            <button
              onClick={registrar} disabled={cargando !== null}
              className="rounded-lg bg-[#2563EB] px-3.5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {cargando === "llave" ? "Registrando…" : "Registrar llave"}
            </button>
          </div>
        ) : (
          <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Tu navegador no soporta WebAuthn.
          </p>
        )}
      </div>

      {/* Códigos de respaldo */}
      <div className="mt-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-700">Códigos de respaldo</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              Códigos de un solo uso para entrar si pierdes tu app o tu llave. Se muestran una sola
              vez al generarlos.
            </p>
          </div>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${respBadge}`}>
            {respTotal === 0 ? "No generados" : `${respDisp} de ${respTotal} disponibles`}
          </span>
        </div>

        {respaldoCodigos ? (
          <div className="mt-5 border-t border-slate-100 pt-5">
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Guárdalos ahora: por seguridad <strong>no se volverán a mostrar</strong>. Cada código
              sirve una sola vez.
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {respaldoCodigos.map((c) => (
                <code key={c} className="rounded-lg bg-slate-50 px-3 py-2 text-center font-mono text-sm tracking-wide text-slate-800 ring-1 ring-slate-100">
                  {c}
                </code>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                onClick={descargarRespaldo}
                className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90"
              >
                Descargar .txt
              </button>
              <button
                onClick={copiarRespaldo}
                className="rounded-lg border border-slate-200 px-3.5 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {copiado ? "¡Copiado!" : "Copiar"}
              </button>
              <button
                onClick={() => setRespaldoCodigos(null)}
                className="ml-auto text-xs text-slate-400 hover:text-slate-600"
              >
                Ya los guardé
              </button>
            </div>
          </div>
        ) : regenMode ? (
          <form
            onSubmit={(e) => { e.preventDefault(); generarRespaldo(regenPass); }}
            className="mt-5 border-t border-slate-100 pt-5"
          >
            <p className="text-sm text-slate-500">
              Al regenerar, <strong>los códigos anteriores dejarán de funcionar</strong>. Confirma con
              tu contraseña.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <input
                type="password" required autoFocus autoComplete="current-password"
                value={regenPass} onChange={(e) => setRegenPass(e.target.value)}
                placeholder="Tu contraseña"
                className="w-56 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
              <button
                type="submit" disabled={cargando !== null || !regenPass}
                className="rounded-lg bg-red-600 px-3.5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {cargando === "respaldo" ? "Regenerando…" : "Regenerar"}
              </button>
              <button
                type="button" onClick={() => { setRegenMode(false); setRegenPass(""); }}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                Cancelar
              </button>
            </div>
          </form>
        ) : (
          <div className="mt-5 border-t border-slate-100 pt-5">
            <p className="text-sm text-slate-500">
              {respTotal > 0
                ? `Te quedan ${respDisp} de ${respTotal} códigos. Si se agotan o los pierdes, regeneralos.`
                : "Genera 10 códigos de un solo uso para no quedarte fuera si pierdes tu segundo factor."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {respTotal > 0 ? (
                <button
                  onClick={() => { setMsg(null); setRegenMode(true); }}
                  disabled={cargando !== null}
                  className="rounded-lg border border-red-200 px-3.5 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  Regenerar códigos
                </button>
              ) : (
                <button
                  onClick={() => generarRespaldo()}
                  disabled={cargando !== null}
                  className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
                >
                  {cargando === "respaldo" ? "Generando…" : "Generar códigos"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
