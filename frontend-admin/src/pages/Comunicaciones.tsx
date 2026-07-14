import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { AdminWhatsAppSesiones } from "../components/AdminWhatsAppSesiones";

interface Config {
  habilitado: boolean;
  url_base: string | null;
  hmac_configurado: boolean;
  timeout_ms: number;
  intervalo_health: number;
  reintentos_default: number;
  estrategia_failover: string;
  cb_umbral: number;
  cb_cooldown: number;
  cb_ventana: number;
  recuperacion_automatica: boolean;
  actualizado?: string;
}

const INK = "#0F1B2D";

export default function Comunicaciones() {
  const [cfg, setCfg] = useState<Config | null>(null);
  const [hmac, setHmac] = useState("");
  const [msg, setMsg] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [cargando, setCargando] = useState<"init" | "guardar" | null>("init");

  async function cargar() {
    try {
      const { data } = await api.get<Config>("/api/admin/comunicaciones/");
      setCfg(data);
    } finally {
      setCargando(null);
    }
  }

  useEffect(() => { cargar(); }, []);

  function set<K extends keyof Config>(k: K, v: Config[K]) {
    setCfg((c) => (c ? { ...c, [k]: v } : c));
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    if (!cfg) return;
    setMsg(null);
    setCargando("guardar");
    try {
      const { data } = await api.put<Config>("/api/admin/comunicaciones/", {
        habilitado: cfg.habilitado,
        url_base: cfg.url_base || null,
        timeout_ms: cfg.timeout_ms,
        intervalo_health: cfg.intervalo_health,
        reintentos_default: cfg.reintentos_default,
        estrategia_failover: cfg.estrategia_failover,
        cb_umbral: cfg.cb_umbral,
        cb_cooldown: cfg.cb_cooldown,
        cb_ventana: cfg.cb_ventana,
        recuperacion_automatica: cfg.recuperacion_automatica,
        ...(hmac ? { hmac_secret: hmac } : {}),
      });
      setCfg(data);
      setHmac("");
      setMsg({ tipo: "ok", texto: "Configuración guardada." });
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo guardar la configuración." });
    } finally {
      setCargando(null);
    }
  }

  if (cargando === "init" || !cfg) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  const inputCls =
    "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Comunicaciones</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Configuración global del Xenty Communication Connector (respaldo de WhatsApp). Rige a
          todos los tenants; cada tenant define su preferencia de proveedores por separado.
        </p>
      </div>

      {msg && (
        <div className={`mb-4 rounded-lg px-4 py-2.5 text-sm ring-1 ${
          msg.tipo === "ok" ? "bg-green-50 text-green-700 ring-green-100" : "bg-red-50 text-red-700 ring-red-100"
        }`}>
          {msg.texto}
        </div>
      )}

      <form onSubmit={guardar} className="space-y-5">
        {/* Master switch */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-700">Connector habilitado</h2>
              <p className="mt-0.5 text-xs text-slate-400">
                Interruptor maestro. Apagado, el Router jamás usa el Connector aunque un tenant lo
                haya elegido — rollback instantáneo sin desplegar nada.
              </p>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                className="peer sr-only"
                checked={cfg.habilitado}
                onChange={(e) => set("habilitado", e.target.checked)}
              />
              <div className="h-6 w-11 rounded-full bg-slate-200 peer-checked:bg-[#2563EB] after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:after:translate-x-5" />
            </label>
          </div>
        </div>

        {/* Conexión al servicio */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Conexión al servicio</h2>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">URL base del Connector</span>
            <input
              type="url"
              value={cfg.url_base ?? ""}
              onChange={(e) => set("url_base", e.target.value)}
              placeholder="https://xcc.interno:8090"
              className={inputCls}
            />
            <span className="mt-1 block text-xs text-slate-400">
              Dirección del contenedor del Connector. Mover el servicio de servidor = cambiar esta URL.
            </span>
          </label>
          <label className="mt-4 block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Secreto HMAC</span>
            <input
              type="password"
              value={hmac}
              onChange={(e) => setHmac(e.target.value)}
              placeholder={cfg.hmac_configurado ? "•••••••• (sin cambios)" : "Pega el secreto compartido"}
              autoComplete="new-password"
              className={inputCls}
            />
            <span className="mt-1 block text-xs text-slate-400">
              Se guarda cifrado (Fernet), nunca en claro. Déjalo vacío para conservar el actual.
            </span>
          </label>
        </div>

        {/* Envío y failover */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Envío y failover</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <NumField label="Timeout por intento (ms)" value={cfg.timeout_ms}
              onChange={(v) => set("timeout_ms", v)} cls={inputCls} min={500} />
            <NumField label="Intervalo de salud (s)" value={cfg.intervalo_health}
              onChange={(v) => set("intervalo_health", v)} cls={inputCls} min={5} />
            <NumField label="Reintentos por defecto" value={cfg.reintentos_default}
              onChange={(v) => set("reintentos_default", v)} cls={inputCls} min={0} max={10} />
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Estrategia de failover</span>
              <select
                value={cfg.estrategia_failover}
                onChange={(e) => set("estrategia_failover", e.target.value)}
                className={inputCls}
              >
                <option value="secuencial">Secuencial (failover en orden)</option>
              </select>
            </label>
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={cfg.recuperacion_automatica}
              onChange={(e) => set("recuperacion_automatica", e.target.checked)}
            />
            <span>Recuperación automática (reincorpora un proveedor al recuperarse)</span>
          </label>
        </div>

        {/* Circuit breaker */}
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
          <h2 className="mb-1 text-sm font-semibold text-slate-700">Circuit breaker</h2>
          <p className="mb-4 text-xs text-slate-400">
            Umbrales por proveedor: tras varios fallos se abre y se salta ese proveedor hasta que
            expira el cooldown, entonces sondea de nuevo.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <NumField label="Fallos para abrir" value={cfg.cb_umbral}
              onChange={(v) => set("cb_umbral", v)} cls={inputCls} min={1} />
            <NumField label="Cooldown (s)" value={cfg.cb_cooldown}
              onChange={(v) => set("cb_cooldown", v)} cls={inputCls} min={1} />
            <NumField label="Ventana de conteo (s)" value={cfg.cb_ventana}
              onChange={(v) => set("cb_ventana", v)} cls={inputCls} min={1} />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={cargando !== null}
            className="rounded-lg bg-[#2563EB] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {cargando === "guardar" ? "Guardando…" : "Guardar cambios"}
          </button>
          {cfg.actualizado && (
            <span className="text-xs text-slate-400">
              Actualizado: {new Date(cfg.actualizado).toLocaleString("es-MX")}
            </span>
          )}
        </div>
      </form>

      <div className="mt-5">
        <AdminWhatsAppSesiones />
      </div>
    </div>
  );
}

function NumField({
  label, value, onChange, cls, min, max,
}: {
  label: string; value: number; onChange: (v: number) => void; cls: string; min?: number; max?: number;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className={cls}
      />
    </label>
  );
}
