import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "../api/client";
import InputPassword from "../components/InputPassword";

export default function Restablecer() {
  const [params]  = useSearchParams();
  const token     = params.get("token") ?? "";
  const navigate  = useNavigate();

  const [password, setPassword] = useState("");
  const [repetir,  setRepetir]  = useState("");
  const [error,    setError]    = useState<string | null>(null);
  const [ok,       setOk]       = useState(false);
  const [loading,  setLoading]  = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (password !== repetir) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/api/auth/proveedores/password/confirmar/", { token, password });
      setOk(true);
      setTimeout(() => navigate("/"), 2500);
    } catch {
      setError("El enlace es inválido o ya expiró. Solicita uno nuevo.");
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
        <div className="mb-8 flex flex-col items-center gap-3">
          <img src={`${import.meta.env.BASE_URL}xenty.png`} alt="Xenty" className="h-12 w-auto" />
          <p className="mt-1 text-sm text-slate-500">Autoservicio de empresas proveedoras</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-panel">
          <h2 className="mb-6 text-base font-bold" style={{ color: "#0F1B2D" }}>
            Nueva contraseña
          </h2>

          {ok ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              Tu contraseña se actualizó. Te llevamos a iniciar sesión…
            </div>
          ) : !token ? (
            <>
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                Enlace incompleto. Solicita un nuevo enlace de restablecimiento.
              </div>
              <Link
                to="/recuperar"
                className="block w-full rounded-lg py-2.5 text-center text-sm font-semibold text-white transition"
                style={{ backgroundColor: "#2563EB" }}
              >
                Solicitar enlace
              </Link>
            </>
          ) : (
            <form onSubmit={onSubmit} className="space-y-4">
              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">Nueva contraseña</span>
                <InputPassword
                  required autoFocus autoComplete="new-password" minLength={8}
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="Al menos 8 caracteres"
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">Repetir contraseña</span>
                <InputPassword
                  required autoComplete="new-password" minLength={8}
                  value={repetir} onChange={(e) => setRepetir(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="••••••••"
                />
              </label>
              <button
                type="submit" disabled={loading}
                className="mt-2 w-full rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                style={{ backgroundColor: "#2563EB" }}
              >
                {loading ? "Guardando…" : "Guardar contraseña"}
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          Xenty Acceso © {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}
