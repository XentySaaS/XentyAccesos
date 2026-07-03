import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

interface Salud {
  estado?: string; plan?: string | null; modo_solo_lectura?: boolean;
  cifrado_fernet_configurado?: boolean; stripe_modo?: string;
  mesa_ayuda_habilitada?: boolean; email_configurado?: boolean; debug?: boolean;
}
interface Config { base_url: string; habilitada: boolean; api_key_configurada: boolean; }

const INK = "#0F1B2D";

function Chip({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
      ok ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-600"
    }`}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: ok ? "#16A34A" : "#94A3B8" }} />
      {label}
    </span>
  );
}

export default function Soporte() {
  const [salud, setSalud]   = useState<Salud | null>(null);
  const [cfg, setCfg]       = useState<Config | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey]   = useState("");
  const [habilitada, setHabilitada] = useState(false);
  const [msg, setMsg]       = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [cargando, setCargando] = useState<string | null>("init");

  async function cargar() {
    try {
      const [s, c] = await Promise.all([
        api.get<Salud>("/api/soporte/salud/"),
        api.get<Config>("/api/soporte/configuracion/"),
      ]);
      setSalud(s.data);
      setCfg(c.data);
      setBaseUrl(c.data.base_url || "");
      setHabilitada(c.data.habilitada);
    } finally {
      setCargando(null);
    }
  }

  useEffect(() => { cargar(); }, []);

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setCargando("guardar"); setMsg(null);
    try {
      const { data } = await api.put<Config>("/api/soporte/configuracion/", {
        base_url: baseUrl, habilitada, ...(apiKey ? { api_key: apiKey } : {}),
      });
      setCfg(data); setApiKey("");
      setMsg({ tipo: "ok", texto: "Configuración guardada." });
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo guardar la configuración." });
    } finally {
      setCargando(null);
    }
  }

  async function probar() {
    setCargando("probar"); setMsg(null);
    try {
      const { data } = await api.post("/api/soporte/probar-conexion/");
      setMsg(data.conectado
        ? { tipo: "ok", texto: `Conexión exitosa (HTTP ${data.status}).` }
        : { tipo: "error", texto: data.detalle || "No se pudo conectar con la Mesa de Ayuda." });
    } catch {
      setMsg({ tipo: "error", texto: "Error al probar la conexión." });
    } finally {
      setCargando(null);
    }
  }

  async function enviar() {
    setCargando("enviar"); setMsg(null);
    try {
      const { data } = await api.post("/api/soporte/enviar-diagnostico/");
      setMsg(data.enviado
        ? { tipo: "ok", texto: "Diagnóstico enviado a la Mesa de Ayuda." }
        : { tipo: "error", texto: data.detalle || "No se envió (Mesa no configurada)." });
    } catch {
      setMsg({ tipo: "error", texto: "Error al enviar el diagnóstico." });
    } finally {
      setCargando(null);
    }
  }

  if (cargando === "init") {
    return <div className="flex items-center justify-center py-24">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" /></div>;
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Soporte · Mesa de Ayuda</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Diagnóstico de configuración (solo lectura) y conexión con la Mesa de Ayuda (Nivel B).
        </p>
      </div>

      {msg && (
        <div className={`mb-4 rounded-lg px-4 py-2.5 text-sm ring-1 ${
          msg.tipo === "ok" ? "bg-green-50 text-green-700 ring-green-100" : "bg-red-50 text-red-700 ring-red-100"
        }`}>{msg.texto}</div>
      )}

      {/* Salud de configuración */}
      <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
        <h2 className="text-sm font-semibold text-slate-700">Salud de configuración</h2>
        {salud && (
          <div className="mt-3 flex flex-wrap gap-2">
            <Chip ok={salud.estado === "activo"} label={`Estado: ${salud.estado}`} />
            <Chip ok={!!salud.plan} label={`Plan: ${salud.plan ?? "—"}`} />
            <Chip ok={!!salud.cifrado_fernet_configurado} label="Cifrado Fernet" />
            <Chip ok={!!salud.email_configurado} label="Email" />
            <Chip ok={salud.stripe_modo === "live"} label={`Stripe: ${salud.stripe_modo}`} />
            <Chip ok={!!salud.mesa_ayuda_habilitada} label="Mesa de Ayuda" />
            <Chip ok={!salud.modo_solo_lectura} label={salud.modo_solo_lectura ? "Solo lectura" : "Escritura ok"} />
            <Chip ok={!salud.debug} label={salud.debug ? "DEBUG on" : "DEBUG off"} />
          </div>
        )}
        <button onClick={enviar} disabled={cargando !== null}
          className="mt-4 rounded-lg border border-slate-200 px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50">
          {cargando === "enviar" ? "Enviando…" : "Enviar diagnóstico a soporte"}
        </button>
      </div>

      {/* Conexión con la Mesa */}
      <form onSubmit={guardar} className="mt-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Conexión con la Mesa de Ayuda</h2>
          {cfg && <Chip ok={cfg.habilitada && !!cfg.base_url} label={cfg.habilitada && cfg.base_url ? "Configurada" : "Sin configurar"} />}
        </div>

        <label className="mt-4 block text-sm">
          <span className="mb-1 flex items-center gap-1.5 font-medium text-slate-700">
            URL base
            <Ayuda>Dirección del servicio de Mesa de Ayuda (p. ej. https://mesa.xenty.mx). El sistema le agrega las rutas de diagnóstico.</Ayuda>
          </span>
          <input type="url" value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
            placeholder="https://mesa.xenty.mx"
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label className="mt-3 block text-sm">
          <span className="mb-1 flex items-center gap-1.5 font-medium text-slate-700">
            API Key
            <Ayuda>Credencial para autenticar contra la Mesa de Ayuda. Se guarda cifrada; déjala vacía para conservar la actual.</Ayuda>
          </span>
          <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
            placeholder={cfg?.api_key_configurada ? "•••••••• (sin cambios)" : "Pega la API key"}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={habilitada} onChange={e => setHabilitada(e.target.checked)} />
          <span className="flex items-center gap-1.5">
            Habilitar la conexión
            <Ayuda>Si está deshabilitada, el sistema no intenta contactar la Mesa (modo local).</Ayuda>
          </span>
        </label>

        <div className="mt-4 flex flex-wrap gap-2">
          <button type="submit" disabled={cargando !== null}
            className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
            {cargando === "guardar" ? "Guardando…" : "Guardar"}
          </button>
          <button type="button" onClick={probar} disabled={cargando !== null}
            className="rounded-lg border border-slate-200 px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50">
            {cargando === "probar" ? "Probando…" : "Probar conexión"}
          </button>
        </div>
      </form>
    </div>
  );
}
