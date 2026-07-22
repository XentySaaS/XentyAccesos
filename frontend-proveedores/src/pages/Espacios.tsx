/**
 * Hub de login de proveedores (proveedores.<dominio>) — "Busca tu espacio de trabajo".
 *
 * Solo descubre espacios: correo → (código de verificación una vez por dispositivo) → lista de
 * espacios → redirige al panel del tenant elegido (<slug>.proveedores.<dominio>), donde ocurre
 * el login real. Sin registro: el alta de proveedores es solo por invitación del recinto.
 */
import { FormEvent, useState } from "react";
import { ArrowRight, Building2 } from "lucide-react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

type Espacio = { nombre: string; dominio: string; url: string };
type Paso = "email" | "codigo" | "lista";

export default function Espacios() {
  const [paso, setPaso] = useState<Paso>("email");
  const [email, setEmail] = useState("");
  const [codigo, setCodigo] = useState("");
  const [espacios, setEspacios] = useState<Espacio[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onBuscar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setAviso(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/publico/proveedores/espacios/", { email });
      if (data.verificado) {
        setEspacios(data.espacios);
        setPaso("lista");
      } else if (data.registrado === false) {
        // Sin cuenta de proveedor activa: se avisa aquí mismo, sin pantalla de código.
        setError(
          "Este correo no tiene una cuenta de proveedor activa. Si te invitaron, completa tu " +
            "registro desde el enlace de la invitación; si no, pide al recinto que te invite."
        );
      } else {
        setPaso("codigo");
      }
    } catch {
      setError("No se pudo buscar tu espacio. Intenta de nuevo en unos minutos.");
    } finally {
      setLoading(false);
    }
  }

  async function onVerificar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setAviso(null);
    setLoading(true);
    try {
      const { data } = await api.post("/api/publico/proveedores/espacios/verificar/", {
        email,
        codigo,
      });
      setEspacios(data.espacios);
      setPaso("lista");
    } catch {
      setError("Código inválido o expirado. Revisa tu correo o solicita uno nuevo.");
    } finally {
      setLoading(false);
    }
  }

  async function reenviar() {
    setError(null);
    setCodigo("");
    try {
      await api.post("/api/publico/proveedores/espacios/", { email });
      setAviso("Te enviamos un nuevo código.");
    } catch {
      setError("No se pudo reenviar el código. Intenta de nuevo en unos minutos.");
    }
  }

  function irAlEspacio(esp: Espacio) {
    // El login real ocurre en el panel del tenant; el correo va prellenado.
    window.location.href = `${esp.url}/?email=${encodeURIComponent(email)}`;
  }

  const inputCls =
    "w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ backgroundColor: "#F1F4F8" }}
    >
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <img src={`${import.meta.env.BASE_URL}xenty.png`} alt="Xenty" className="h-12 w-auto" />
          <p className="mt-1 text-sm text-slate-500">Busca tu espacio de trabajo</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-panel">
          {paso === "email" && (
            <>
              <h2 className="text-base font-bold" style={{ color: "#0F1B2D" }}>
                Iniciar sesión
              </h2>
              <p className="mb-6 mt-1 text-sm text-slate-500">
                Ingresa tu correo para encontrar tu cuenta.
              </p>
              {error && (
                <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
              <form onSubmit={onBuscar} className="space-y-4">
                <label className="block text-sm">
                  <span className="mb-1 flex items-center gap-1.5 font-medium text-slate-700">
                    Correo electrónico
                    <Ayuda>
                      El correo con el que te registraste como proveedor. Si trabajas con varios
                      recintos, verás todos tus espacios y podrás elegir en cuál entrar.
                    </Ayuda>
                  </span>
                  <input
                    type="email" required autoComplete="email" autoFocus
                    value={email} onChange={(e) => setEmail(e.target.value)}
                    className={inputCls} placeholder="usuario@empresa.com"
                  />
                </label>
                <button
                  type="submit" disabled={loading}
                  className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                  style={{ backgroundColor: "#2563EB" }}
                >
                  {loading ? "Buscando…" : "Continuar"} {!loading && <ArrowRight className="h-4 w-4" />}
                </button>
              </form>
            </>
          )}

          {paso === "codigo" && (
            <>
              <h2 className="text-base font-bold" style={{ color: "#0F1B2D" }}>
                Verifica tu correo
              </h2>
              <p className="mb-6 mt-1 text-sm text-slate-500">
                Enviamos un código de 6 dígitos a <strong>{email}</strong> (válido 10 minutos).
                Solo se pide la primera vez en este dispositivo.
              </p>
              {aviso && !error && (
                <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                  {aviso}
                </div>
              )}
              {error && (
                <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
              <form onSubmit={onVerificar} className="space-y-4">
                <label className="block text-sm">
                  <span className="mb-1 flex items-center gap-1.5 font-medium text-slate-700">
                    Código de verificación
                    <Ayuda>
                      Código de 6 dígitos que enviamos a tu correo. Confirma que el correo es tuyo
                      antes de mostrarte tus espacios de trabajo (protege tu privacidad).
                    </Ayuda>
                  </span>
                  <input
                    inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required autoFocus
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
                    className={`${inputCls} text-center text-lg tracking-[0.4em]`}
                    placeholder="••••••"
                  />
                </label>
                <button
                  type="submit" disabled={loading || codigo.length !== 6}
                  className="mt-2 w-full rounded-lg py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                  style={{ backgroundColor: "#2563EB" }}
                >
                  {loading ? "Verificando…" : "Verificar"}
                </button>
              </form>
              <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                <button onClick={() => { setPaso("email"); setCodigo(""); setError(null); setAviso(null); }} className="transition hover:text-slate-600">
                  Usar otro correo
                </button>
                <button onClick={reenviar} className="transition hover:text-slate-600">
                  Reenviar código
                </button>
              </div>
              <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-500">
                ¿No llega el código? Revisa tu carpeta de spam o usa «Reenviar código». Por
                seguridad se permiten máximo 3 envíos por hora.
              </p>
            </>
          )}

          {paso === "lista" && (
            <>
              <h2 className="text-base font-bold" style={{ color: "#0F1B2D" }}>
                {espacios.length > 0
                  ? `Encontramos ${espacios.length} espacio${espacios.length === 1 ? "" : "s"} de trabajo`
                  : "Sin espacios activos"}
              </h2>
              <p className="mb-6 mt-1 break-all text-sm text-slate-500">para {email}</p>
              {espacios.length === 0 ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Este correo no tiene espacios de trabajo activos. El registro de proveedores es
                  por invitación: pide al recinto con el que trabajas que te invite.
                </div>
              ) : (
                <div className="space-y-2">
                  {espacios.map((esp) => (
                    <button
                      key={esp.dominio}
                      onClick={() => irAlEspacio(esp)}
                      className="flex w-full items-center gap-3 rounded-lg border border-slate-200 px-4 py-3 text-left transition hover:border-blue-300 hover:bg-blue-50/50"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100">
                        <Building2 className="h-4 w-4 text-slate-500" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-slate-800">
                          {esp.nombre}
                        </span>
                        <span className="block truncate text-xs text-slate-400">{esp.dominio}</span>
                      </span>
                      <ArrowRight className="h-4 w-4 shrink-0 text-slate-400" />
                    </button>
                  ))}
                </div>
              )}
              <button
                onClick={() => { setPaso("email"); setCodigo(""); setError(null); setAviso(null); }}
                className="mt-4 block w-full text-center text-xs text-slate-400 transition hover:text-slate-600"
              >
                Buscar con otro correo
              </button>
            </>
          )}
        </div>

        <div className="mt-6 flex flex-col items-center gap-1.5 text-center text-xs text-slate-400">
          <span>Xenty Accesos © {new Date().getFullYear()}</span>
          <span>¿Sin cuenta? El registro es por invitación del recinto con el que trabajas.</span>
        </div>
      </div>
    </div>
  );
}
