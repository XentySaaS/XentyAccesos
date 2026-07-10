import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";

export default function Recuperar() {
  const [email, setEmail]     = useState("");
  const [enviado, setEnviado] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      // La respuesta es genérica (no revela si el correo existe). Mostramos éxito siempre.
      await api.post("/api/auth/acceso/password/solicitar/", { email });
    } catch {
      /* aun ante error de red mostramos el mismo mensaje para no filtrar cuentas */
    } finally {
      setEnviado(true);
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
          <p className="mt-1 text-sm text-slate-500">Control de accesos a recintos</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-panel">
          <h2 className="mb-6 text-base font-bold" style={{ color: "#0F1B2D" }}>
            Recuperar contraseña
          </h2>

          {enviado ? (
            <>
              <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.
                Revisa tu bandeja de entrada (y la carpeta de spam). El enlace vence en 1 hora.
              </div>
              <Link
                to="/"
                className="block w-full rounded-lg py-2.5 text-center text-sm font-semibold text-white transition"
                style={{ backgroundColor: "#2563EB" }}
              >
                Volver a iniciar sesión
              </Link>
            </>
          ) : (
            <form onSubmit={onSubmit} className="space-y-4">
              <p className="text-sm text-slate-500">
                Escribe tu correo y te enviaremos un enlace para crear una nueva contraseña.
              </p>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">Correo electrónico</span>
                <input
                  type="email" required autoFocus autoComplete="email"
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  placeholder="usuario@empresa.com"
                />
              </label>
              <button
                type="submit" disabled={loading}
                className="mt-2 w-full rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                style={{ backgroundColor: "#2563EB" }}
              >
                {loading ? "Enviando…" : "Enviar enlace"}
              </button>
              <Link
                to="/"
                className="block w-full text-center text-xs text-slate-400 transition hover:text-slate-600"
              >
                Volver a iniciar sesión
              </Link>
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
