import { CalendarCheck, QrCode, ShieldCheck, Users } from "lucide-react";
import { FormEvent, useState } from "react";
import api from "./api";
import InputPassword from "./InputPassword";

interface Resultado {
  tenant: string;
  dominio: string;
  estado: string;
}

const FEATURES = [
  { icon: CalendarCheck, t: "Eventos y citas", d: "Programa eventos, invita proveedores y gestiona visitas con cupos y vigencias." },
  { icon: QrCode, t: "Gafetes QR seguros", d: "Credenciales firmadas e inviolables; escaneo en torniquetes y plumas." },
  { icon: Users, t: "Proveedores y documentos", d: "Onboarding self-service, validación documental y plantillas de empleados." },
  { icon: ShieldCheck, t: "Cumplimiento 69-B", d: "Validación de RFC contra la lista del SAT y control de acceso por reglas." },
];

export default function App() {
  const [f, setF] = useState({
    nombre: "", subdominio: "", admin_nombre: "", admin_email: "", admin_password: "",
  });
  const [ok, setOk] = useState<Resultado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: k === "subdominio" ? e.target.value.toLowerCase().replace(/[^a-z0-9]/g, "") : e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const { data } = await api.post<Resultado>("/api/signup/", f);
      setOk(data);
    } catch (err) {
      const detalle = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detalle ?? "No se pudo crear la cuenta. Revisa los datos.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 text-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <img src="/xenty-white.png" alt="Xenty Accesos" className="h-8 w-auto" />
        <a href="#crear" className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium hover:bg-emerald-400">
          Crear cuenta
        </a>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 py-12 md:grid-cols-2">
        <div>
          <h1 className="text-4xl font-extrabold leading-tight md:text-5xl">
            Control de accesos para recintos, <span className="text-emerald-400">sin fricción</span>.
          </h1>
          <p className="mt-4 text-lg text-slate-300">
            Eventos, proveedores, gafetes QR, dispositivos edge y cumplimiento SAT 69-B en una sola
            plataforma multitenant. Tu espacio queda listo en minutos.
          </p>
          <div className="mt-6 flex gap-3">
            <a href="#crear" className="rounded-lg bg-emerald-500 px-5 py-3 font-medium hover:bg-emerald-400">
              Empezar gratis
            </a>
            <span className="self-center text-sm text-slate-400">14 días de prueba · sin tarjeta</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {FEATURES.map((feat) => (
            <div key={feat.t} className="rounded-xl bg-white/5 p-5 ring-1 ring-white/10">
              <feat.icon className="h-7 w-7 text-emerald-400" />
              <h3 className="mt-3 font-semibold">{feat.t}</h3>
              <p className="mt-1 text-sm text-slate-300">{feat.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="crear" className="mx-auto max-w-md px-6 py-16">
        <div className="rounded-2xl bg-white p-8 text-slate-900 shadow-2xl">
          {ok ? (
            <div className="space-y-3 text-center">
              <h2 className="text-2xl font-bold">¡Cuenta creada! 🎉</h2>
              <p className="text-slate-600">
                Tu espacio <b>{ok.tenant}</b> está en <b>{ok.estado}</b>. Accede en:
              </p>
              <code className="block break-all rounded-lg bg-slate-100 p-3 text-sm">{ok.dominio}</code>
              <p className="text-sm text-slate-500">
                Inicia sesión con el correo y la contraseña que registraste.
              </p>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="space-y-3">
              <h2 className="text-2xl font-bold">Crea tu cuenta</h2>
              {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
              <input className="w-full rounded-lg border px-3 py-2" placeholder="Nombre de la empresa"
                value={f.nombre} onChange={set("nombre")} required />
              <div>
                <input className="w-full rounded-lg border px-3 py-2" placeholder="Subdominio (ej. rayados)"
                  value={f.subdominio} onChange={set("subdominio")} required minLength={3} />
                {f.subdominio && (
                  <p className="mt-1 text-xs text-slate-500">Tu URL: {f.subdominio}.xenty.mx</p>
                )}
              </div>
              <input className="w-full rounded-lg border px-3 py-2" placeholder="Tu nombre"
                value={f.admin_nombre} onChange={set("admin_nombre")} required />
              <input className="w-full rounded-lg border px-3 py-2" type="email" placeholder="Tu correo"
                value={f.admin_email} onChange={set("admin_email")} required />
              <InputPassword className="w-full rounded-lg border px-3 py-2"
                placeholder="Contraseña (mín. 8)" value={f.admin_password}
                onChange={set("admin_password")} required minLength={8} />
              <button disabled={enviando}
                className="w-full rounded-lg bg-slate-900 py-3 font-medium text-white disabled:opacity-50"
                type="submit">
                {enviando ? "Creando tu espacio…" : "Crear y empezar"}
              </button>
            </form>
          )}
        </div>
      </section>

      <footer className="border-t border-white/10 py-8 text-center text-sm text-slate-400">
        © Xenty SaaS — Xenty Accesos
      </footer>
    </div>
  );
}
