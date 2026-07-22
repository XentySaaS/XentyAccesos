import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "../api/client";
import InputPassword from "../components/InputPassword";
import { useAuth } from "../store/auth";

/** URL del hub (selector de espacios): el host del panel sin su primer label.
 *  'museos.proveedores.localhost:8080' → 'proveedores.localhost:8080'. */
function urlHub(): string | null {
  const { protocol, hostname, port } = window.location;
  const labels = hostname.split(".");
  if (labels[1] !== "proveedores") return null; // host atípico: no ofrecer el link
  return `${protocol}//${labels.slice(1).join(".")}${port ? `:${port}` : ""}/`;
}

export default function Login() {
  const [params]    = useSearchParams();
  // El hub (proveedores.<dominio>) redirige aquí con el correo ya verificado como prefill.
  const [email,    setEmail]    = useState(params.get("email") ?? "");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [recinto,  setRecinto]  = useState<string | null>(null);
  const setTokens   = useAuth((s) => s.setTokens);
  const navigate    = useNavigate();
  const sesionExp   = params.get("sesion") === "expirada";
  const hub         = urlHub();

  // Marca del recinto (pública): que se vea EN QUÉ espacio se está iniciando sesión.
  useEffect(() => {
    api.get<{ nombre: string }>("/api/publico/marca/")
      .then(({ data }) => { if (data.nombre) setRecinto(data.nombre); })
      .catch(() => {});
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/auth/proveedores/login/", { email, password });
      setTokens(data.access, data.refresh);
      navigate("/dashboard");
    } catch {
      setError("Correo o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ backgroundColor: "#F1F4F8" }}
    >
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <img src={`${import.meta.env.BASE_URL}xenty.png`} alt="Xenty" className="h-12 w-auto" />
          <div className="text-center">
            <p className="mt-1 text-sm text-slate-500">
              {recinto ? (
                <>Portal de proveedores de <strong className="text-slate-700">{recinto}</strong></>
              ) : (
                "Autoservicio de empresas proveedoras"
              )}
            </p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-white p-8 shadow-panel">
          <h2 className="mb-6 text-base font-bold" style={{ color: "#0F1B2D" }}>
            Iniciar sesión
          </h2>

          {sesionExp && !error && (
            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Tu sesión expiró. Inicia sesión nuevamente.
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={onSubmit} className="space-y-4">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Correo electrónico</span>
              <input
                type="email" required autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                placeholder="usuario@empresa.com"
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

            <Link
              to="/recuperar"
              className="block text-center text-xs text-slate-400 transition hover:text-slate-600"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </form>

          {hub && (
            <a
              href={hub}
              className="mt-3 block text-center text-xs text-slate-400 transition hover:text-slate-600"
            >
              ← Elegir otro espacio de trabajo
            </a>
          )}
        </div>

        <div className="mt-6 flex flex-col items-center gap-1.5 text-center text-xs text-slate-400">
          <span>Xenty Accesos © {new Date().getFullYear()}</span>
          <nav className="flex items-center gap-4">
            <Link to="/legal/aviso-privacidad" className="transition hover:text-slate-600">
              Aviso de Privacidad
            </Link>
            <Link to="/legal/terminos" className="transition hover:text-slate-600">
              Términos y Condiciones
            </Link>
          </nav>
        </div>
      </div>
    </div>
  );
}
