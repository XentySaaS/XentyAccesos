import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import InputPassword from "../components/InputPassword";
import { mfaPendiente } from "../lib/jwt";
import { autenticarLlave, webauthnDisponible } from "../lib/webauthn";
import { useAuth } from "../store/auth";

type Fase = "credenciales" | "mfa" | "enrolar";

export default function Login() {
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [codigo,   setCodigo]   = useState("");
  const [modoRespaldo, setModoRespaldo] = useState(false);
  const [respaldo, setRespaldo] = useState("");
  const [fase,     setFase]     = useState<Fase>("credenciales");
  const [qr,       setQr]       = useState<string | null>(null);
  const [secret,   setSecret]   = useState<string | null>(null);
  const [error,    setError]    = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);
  const setTokens = useAuth((s) => s.setTokens);
  const logout    = useAuth((s) => s.logout);
  const navigate  = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/admin/login/", { email, password });
      // Se guardan los tokens (aunque sean de sesión MFA pendiente): el cliente los usa como
      // Authorization para enrolar/verificar el 2º factor.
      setTokens(data.access, data.refresh);
      if (data.mfa_enrolar) {
        // MFA obligatorio y sin factor enrolado: pedir el enrolamiento (QR) a fuerza.
        const { data: enrol } = await api.post("/api/admin/mfa/totp/enrolar/", {});
        setQr(enrol.qr);
        setSecret(enrol.secret);
        setFase("enrolar");
      } else if (data.mfa_pendiente || mfaPendiente(data.access)) {
        setFase("mfa");
      } else {
        navigate("/dashboard");
      }
    } catch {
      setError("Correo o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  // Enrolamiento obligatorio: activar prueba el 2º factor y devuelve tokens 'full' en un solo paso.
  async function onEnrolar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/admin/mfa/totp/activar/", { codigo });
      setTokens(data.access, data.refresh);
      navigate("/dashboard");
    } catch {
      setError("Código inválido. Revisa tu app autenticadora e inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  async function onVerificar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/admin/mfa/verificar/", { codigo });
      setTokens(data.access, data.refresh);
      navigate("/dashboard");
    } catch {
      setError("Código inválido. Revisa tu app autenticadora.");
    } finally {
      setLoading(false);
    }
  }

  async function onVerificarRespaldo(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/admin/mfa/respaldo/verificar/", { codigo: respaldo });
      setTokens(data.access, data.refresh);
      navigate("/dashboard");
    } catch {
      setError("Código de respaldo inválido o ya usado.");
    } finally {
      setLoading(false);
    }
  }

  async function onLlave() {
    setError(null);
    setLoading(true);
    try {
      const data = await autenticarLlave();
      setTokens(data.access, data.refresh);
      navigate("/dashboard");
    } catch {
      setError("No se pudo verificar con la llave de seguridad.");
    } finally {
      setLoading(false);
    }
  }

  function cancelar() {
    logout();
    setFase("credenciales");
    setCodigo("");
    setPassword("");
    setModoRespaldo(false);
    setRespaldo("");
    setQr(null);
    setSecret(null);
    setError(null);
  }

  const titulo =
    fase === "credenciales"
      ? "Iniciar sesión"
      : fase === "enrolar"
        ? "Configura tu segundo factor"
        : "Verificación en dos pasos";

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ backgroundColor: "#F1F4F8" }}
    >
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <img src={`${import.meta.env.BASE_URL}xenty.png`} alt="Xenty" className="h-12 w-auto" />
          <p className="mt-1 text-sm text-slate-500">Control plane · super-administración</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-white p-8 shadow-panel">
          <h2 className="mb-6 text-base font-bold" style={{ color: "#0F1B2D" }}>
            {titulo}
          </h2>

          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {fase === "credenciales" && (
            <form onSubmit={onSubmit} className="space-y-4">
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">Correo electrónico</span>
                <input
                  type="email" required autoComplete="email"
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="admin@xenty.mx"
                />
              </label>

              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">Contraseña</span>
                <InputPassword
                  required autoComplete="current-password"
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="••••••••"
                />
              </label>

              <button
                type="submit" disabled={loading}
                className="mt-2 w-full rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                style={{ backgroundColor: "#2563EB" }}
              >
                {loading ? "Verificando…" : "Entrar"}
              </button>
            </form>
          )}

          {fase === "enrolar" && (
            <form onSubmit={onEnrolar} className="space-y-4">
              <p className="text-sm text-slate-500">
                Este panel exige verificación en dos pasos. Escanea el código con tu app autenticadora
                (Google Authenticator, 1Password, Authy…) y escribe el código de 6 dígitos que genere.
              </p>
              {qr && (
                <div className="flex justify-center">
                  <img
                    src={qr} alt="Código QR de configuración MFA"
                    className="h-44 w-44 rounded-lg border border-slate-200 p-2"
                  />
                </div>
              )}
              {secret && (
                <p className="text-center text-[11px] text-slate-400">
                  ¿No puedes escanear? Clave: <span className="font-mono text-slate-600">{secret}</span>
                </p>
              )}
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">Código de verificación</span>
                <input
                  type="text" required autoFocus inputMode="numeric" autoComplete="one-time-code"
                  maxLength={6} value={codigo}
                  onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-center text-lg tracking-[0.4em] outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="000000"
                />
              </label>
              <button
                type="submit" disabled={loading || codigo.length < 6}
                className="mt-2 w-full rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                style={{ backgroundColor: "#2563EB" }}
              >
                {loading ? "Activando…" : "Activar y entrar"}
              </button>
              <button
                type="button" onClick={cancelar}
                className="w-full text-center text-xs text-slate-400 hover:text-slate-600"
              >
                Cancelar y volver
              </button>
            </form>
          )}

          {fase === "mfa" &&
            (modoRespaldo ? (
              <form onSubmit={onVerificarRespaldo} className="space-y-4">
                <p className="text-sm text-slate-500">
                  Ingresa uno de tus códigos de respaldo (de un solo uso).
                </p>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700">Código de respaldo</span>
                  <input
                    type="text" required autoFocus autoComplete="one-time-code" value={respaldo}
                    onChange={(e) => setRespaldo(e.target.value.toUpperCase())}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-center font-mono text-sm tracking-widest outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    placeholder="XXXX-XXXX-XXXX"
                  />
                </label>
                <button
                  type="submit" disabled={loading || respaldo.replace(/[^A-Za-z0-9]/g, "").length < 12}
                  className="mt-2 w-full rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                  style={{ backgroundColor: "#2563EB" }}
                >
                  {loading ? "Verificando…" : "Verificar"}
                </button>
                <button
                  type="button" onClick={() => { setModoRespaldo(false); setRespaldo(""); setError(null); }}
                  className="w-full text-center text-xs text-slate-400 hover:text-slate-600"
                >
                  Volver al código de la app
                </button>
              </form>
            ) : (
              <form onSubmit={onVerificar} className="space-y-4">
                <p className="text-sm text-slate-500">
                  Ingresa el código de 6 dígitos de tu app autenticadora.
                </p>
                <label className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700">Código de verificación</span>
                  <input
                    type="text" required autoFocus inputMode="numeric" autoComplete="one-time-code"
                    maxLength={6} value={codigo}
                    onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-center text-lg tracking-[0.4em] outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    placeholder="000000"
                  />
                </label>

                <button
                  type="submit" disabled={loading || codigo.length < 6}
                  className="mt-2 w-full rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                  style={{ backgroundColor: "#2563EB" }}
                >
                  {loading ? "Verificando…" : "Verificar"}
                </button>
                {webauthnDisponible() && (
                  <>
                    <div className="flex items-center gap-3 py-1">
                      <span className="h-px flex-1 bg-slate-100" />
                      <span className="text-[11px] uppercase tracking-wide text-slate-400">o</span>
                      <span className="h-px flex-1 bg-slate-100" />
                    </div>
                    <button
                      type="button" onClick={onLlave} disabled={loading}
                      className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
                      Usar llave de seguridad
                    </button>
                  </>
                )}
                <button
                  type="button" onClick={() => { setModoRespaldo(true); setError(null); }}
                  className="w-full text-center text-xs text-slate-400 hover:text-slate-600"
                >
                  ¿No tienes tu app ni tu llave? Usa un código de respaldo
                </button>
                <button
                  type="button" onClick={cancelar}
                  className="w-full text-center text-xs text-slate-400 hover:text-slate-600"
                >
                  Cancelar y volver
                </button>
              </form>
            ))}
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          Panel interno · acceso restringido
        </p>
      </div>
    </div>
  );
}
