import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";
import InputPassword from "../components/InputPassword";
import { registrarLlave, webauthnDisponible } from "../lib/webauthn";

interface Me {
  email?: string;
  mfa_habilitado?: boolean;
  totp_habilitado?: boolean;
  webauthn_credenciales?: number;
  codigos_respaldo_disponibles?: number;
  codigos_respaldo_total?: number;
}
interface Enrolamiento {
  secret: string;
  otpauth_uri: string;
  qr: string;
}

const INK = "#0F1B2D";
const SIGNAL = "#2563EB";

export default function Seguridad() {
  const [me, setMe] = useState<Me | null>(null);
  const [enrol, setEnrol] = useState<Enrolamiento | null>(null);
  const [codigo, setCodigo] = useState("");
  const [nombreLlave, setNombreLlave] = useState("");
  const [msg, setMsg] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [cargando, setCargando] = useState<string | null>("init");
  // Códigos de respaldo: se muestran una sola vez tras generarlos.
  const [respaldoCodigos, setRespaldoCodigos] = useState<string[] | null>(null);
  const [regenMode, setRegenMode] = useState(false);
  const [regenPass, setRegenPass] = useState("");
  const [copiado, setCopiado] = useState(false);

  async function cargarMe() {
    try {
      const { data } = await api.get<Me>("/api/auth/me/");
      setMe(data);
    } finally {
      setCargando(null);
    }
  }
  useEffect(() => {
    cargarMe();
  }, []);

  async function enrolar() {
    setMsg(null);
    setCargando("enrolar");
    try {
      const { data } = await api.post<Enrolamiento>("/api/auth/mfa/totp/enrolar/");
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
      await api.post("/api/auth/mfa/totp/activar/", { codigo });
      setEnrol(null);
      setCodigo("");
      setMsg({ tipo: "ok", texto: "MFA por código activado." });
      await cargarMe();
    } catch {
      setMsg({ tipo: "error", texto: "Código inválido. Intenta de nuevo." });
    } finally {
      setCargando(null);
    }
  }

  async function desactivar() {
    if (!window.confirm("¿Desactivar el código de app (TOTP)? Podrás volver a configurarlo cuando quieras.")) return;
    setMsg(null);
    setCargando("desactivar");
    try {
      await api.post("/api/auth/mfa/totp/desactivar/");
      setEnrol(null);
      setMsg({ tipo: "ok", texto: "Código de app (TOTP) desactivado." });
      await cargarMe();
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo desactivar el TOTP." });
    } finally {
      setCargando(null);
    }
  }

  async function registrar() {
    setMsg(null);
    setCargando("llave");
    try {
      await registrarLlave(nombreLlave.trim() || "Llave de seguridad");
      setNombreLlave("");
      setMsg({ tipo: "ok", texto: "Llave registrada correctamente." });
      await cargarMe();
    } catch {
      setMsg({
        tipo: "error",
        texto: "No se pudo registrar la llave (cancelada o no compatible).",
      });
    } finally {
      setCargando(null);
    }
  }

  async function generarRespaldo(password?: string) {
    setMsg(null);
    setCargando("respaldo");
    try {
      const { data } = await api.post<{ codigos: string[] }>(
        "/api/auth/mfa/respaldo/generar/",
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
      `Códigos de respaldo — Xenty Accesos\n${me?.email ?? ""}\n` +
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

  if (cargando === "init") {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  const totp = me?.totp_habilitado === true;
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
        <h1 className="text-xl font-bold" style={{ color: INK }}>
          Seguridad
        </h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Protege tu cuenta con un segundo factor: código de tu app autenticadora, una llave de
          seguridad (passkey) o códigos de respaldo.
        </p>
      </div>

      {msg && (
        <div
          className={`mb-4 rounded-lg px-4 py-2.5 text-sm ring-1 ${
            msg.tipo === "ok"
              ? "bg-green-50 text-green-700 ring-green-100"
              : "bg-red-50 text-red-700 ring-red-100"
          }`}
        >
          {msg.texto}
        </div>
      )}

      {/* TOTP */}
      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            Código de app (TOTP)
            <Ayuda>
              Usa una app como Google Authenticator, Authy o 1Password para generar códigos de 6
              dígitos.
            </Ayuda>
          </h2>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              totp ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-600"
            }`}
          >
            {totp ? "Activado" : "No configurado"}
          </span>
        </div>

        {!enrol ? (
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={enrolar}
              disabled={cargando !== null}
              className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {cargando === "enrolar" ? "Generando…" : totp ? "Reconfigurar" : "Configurar código"}
            </button>
            {totp && (
              <button
                onClick={desactivar}
                disabled={cargando !== null}
                className="rounded-lg border border-red-200 px-3.5 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {cargando === "desactivar" ? "Desactivando…" : "Desactivar"}
              </button>
            )}
          </div>
        ) : (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="text-xs text-slate-500">
              Escanea el QR con tu app e ingresa el código que genera.
            </p>
            <div className="mt-3 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
              <img
                src={enrol.qr}
                alt="Código QR"
                className="h-40 w-40 rounded-lg bg-white p-2 ring-1 ring-slate-100"
              />
              <code className="block break-all rounded-lg bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800 ring-1 ring-slate-100">
                {enrol.secret}
              </code>
            </div>
            <form onSubmit={activar} className="mt-3 flex flex-wrap items-center gap-2">
              <input
                type="text" required inputMode="numeric" maxLength={6} value={codigo}
                onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                className="w-40 rounded-lg border border-slate-200 px-3 py-2 text-center text-lg tracking-[0.3em] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
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
          </div>
        )}
      </div>

      {/* WebAuthn */}
      <div className="mt-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            Llaves de seguridad (WebAuthn)
            <Ayuda>
              Passkeys o llaves físicas (FIDO2, p. ej. una YubiKey o la huella/rostro de tu
              dispositivo) como segundo factor.
            </Ayuda>
          </h2>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
            {me?.webauthn_credenciales ?? 0} registrada(s)
          </span>
        </div>
        {webauthnDisponible() ? (
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              type="text" value={nombreLlave} maxLength={80}
              onChange={(e) => setNombreLlave(e.target.value)}
              placeholder="Nombre de la llave (ej. YubiKey, mi teléfono)"
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
            <button
              onClick={registrar} disabled={cargando !== null}
              className="rounded-lg px-3.5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              style={{ backgroundColor: SIGNAL }}
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
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            Códigos de respaldo
            <Ayuda>
              Códigos de un solo uso para entrar si pierdes el acceso a tu app o tu llave. Se muestran
              una sola vez al generarlos; guárdalos en un lugar seguro.
            </Ayuda>
          </h2>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${respBadge}`}>
            {respTotal === 0 ? "No generados" : `${respDisp} de ${respTotal} disponibles`}
          </span>
        </div>

        {respaldoCodigos ? (
          <div className="mt-4 border-t border-slate-100 pt-4">
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
            className="mt-4 border-t border-slate-100 pt-4"
          >
            <p className="text-xs text-slate-500">
              Al regenerar, <strong>los códigos anteriores dejarán de funcionar</strong>. Confirma con
              tu contraseña.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <InputPassword
                required autoFocus autoComplete="current-password"
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
          <div className="mt-4">
            <p className="text-xs text-slate-500">
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
