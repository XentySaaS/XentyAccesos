import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";

interface Resultado {
  tenant: string;
  dominio: string;
  estado: string;
}

export default function Signup() {
  const [f, setF] = useState({
    nombre: "", subdominio: "", admin_nombre: "", admin_email: "", admin_password: "",
  });
  const [ok, setOk] = useState<Resultado | null>(null);
  const [error, setError] = useState<string | null>(null);

  function set(campo: keyof typeof f) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [campo]: e.target.value });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const { data } = await api.post<Resultado>("/api/signup/", f);
      setOk(data);
    } catch (err) {
      const detalle = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detalle ?? "No se pudo crear la cuenta.");
    }
  }

  if (ok) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-96 space-y-3 rounded-xl bg-white p-8 shadow">
          <h1 className="text-xl font-semibold">¡Cuenta creada! 🎉</h1>
          <p className="text-sm text-slate-600">
            Tu espacio <b>{ok.tenant}</b> quedó en <b>{ok.estado}</b>. Accede en:
          </p>
          <code className="block break-all rounded bg-slate-100 p-2 text-sm">{ok.dominio}</code>
          <Link className="block text-center text-sm text-slate-900 underline" to="/">
            Ir al inicio
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form onSubmit={onSubmit} className="w-96 space-y-3 rounded-xl bg-white p-8 shadow">
        <h1 className="text-xl font-semibold">Crear cuenta de empresa</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <input className="w-full rounded border px-3 py-2" placeholder="Nombre de la empresa"
          value={f.nombre} onChange={set("nombre")} required />
        <input className="w-full rounded border px-3 py-2" placeholder="Subdominio (ej. rayados)"
          value={f.subdominio} onChange={set("subdominio")} required />
        <input className="w-full rounded border px-3 py-2" placeholder="Nombre del administrador"
          value={f.admin_nombre} onChange={set("admin_nombre")} required />
        <input className="w-full rounded border px-3 py-2" type="email" placeholder="Correo del administrador"
          value={f.admin_email} onChange={set("admin_email")} required />
        <input className="w-full rounded border px-3 py-2" type="password" placeholder="Contraseña (mín. 8)"
          value={f.admin_password} onChange={set("admin_password")} required minLength={8} />
        <button className="w-full rounded bg-slate-900 py-2 text-white" type="submit">
          Crear y aprovisionar
        </button>
        <p className="text-center text-sm text-slate-500">
          ¿Ya tienes cuenta? <Link className="text-slate-900 underline" to="/">Entrar</Link>
        </p>
      </form>
    </div>
  );
}
