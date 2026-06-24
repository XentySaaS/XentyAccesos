import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const setTokens = useAuth((s) => s.setTokens);
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const { data } = await api.post("/api/auth/acceso/login/", { email, password });
      setTokens(data.access, data.refresh);
      navigate("/dashboard");
    } catch {
      setError("Credenciales invalidas.");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form onSubmit={onSubmit} className="w-80 space-y-4 rounded-xl bg-white p-8 shadow">
        <h1 className="text-xl font-semibold">Xenty Acceso</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <input className="w-full rounded border px-3 py-2" type="email" placeholder="Correo"
          value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full rounded border px-3 py-2" type="password" placeholder="Contrasena"
          value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="w-full rounded bg-slate-900 py-2 text-white" type="submit">
          Entrar
        </button>
      </form>
    </div>
  );
}
