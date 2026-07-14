import { useEffect, useRef, useState } from "react";
import api from "../api/client";
import { Ayuda } from "./Ayuda";

interface Estado {
  connection_id: string;
  state: string;
  connected: boolean;
  has_qr: boolean;
}

/**
 * Vinculación del WhatsApp del Connector para el tenant. El navegador NO habla con el XCC: pega al
 * backend (`/api/mensajeria/whatsapp/*`), que firma por HMAC. Muestra estado, QR (con polling hasta
 * conectar) y desvincular.
 */
export function WhatsAppVinculacion() {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [accion, setAccion] = useState<"vincular" | "desvincular" | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const poll = useRef<ReturnType<typeof setInterval>>();

  async function cargarEstado(): Promise<Estado | null> {
    try {
      const { data } = await api.get<Estado>("/api/mensajeria/whatsapp/sesion/");
      setEstado(data);
      return data;
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || "No se pudo consultar el estado.");
      return null;
    } finally {
      setCargando(false);
    }
  }

  async function cargarQr() {
    try {
      const { data } = await api.get<{ qr?: string | null }>("/api/mensajeria/whatsapp/qr/");
      setQr(data.qr ?? null);
    } catch {
      /* aún sin QR */
    }
  }

  function pararPolling() {
    if (poll.current) {
      clearInterval(poll.current);
      poll.current = undefined;
    }
  }

  useEffect(() => {
    cargarEstado();
    return pararPolling;
  }, []);

  useEffect(() => {
    if (estado?.connected) {
      pararPolling();
      setQr(null);
    }
  }, [estado?.connected]);

  async function vincular() {
    setAccion("vincular");
    setMsg(null);
    try {
      await api.post("/api/mensajeria/whatsapp/sesion/");
      pararPolling();
      // Baileys tarda 1-2s en emitir el QR; luego se refresca cada 3s hasta conectar (el QR rota).
      setTimeout(cargarQr, 1500);
      poll.current = setInterval(async () => {
        const e = await cargarEstado();
        if (e && !e.connected) cargarQr();
      }, 3000);
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || "No se pudo iniciar la vinculación.");
    } finally {
      setAccion(null);
    }
  }

  async function desvincular() {
    setAccion("desvincular");
    setMsg(null);
    pararPolling();
    try {
      await api.delete("/api/mensajeria/whatsapp/sesion/");
      setQr(null);
      await cargarEstado();
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || "No se pudo desvincular.");
    } finally {
      setAccion(null);
    }
  }

  const conectado = !!estado?.connected;
  const etiquetaEstado = conectado
    ? "Conectado"
    : estado?.state === "qr" || estado?.state === "connecting"
      ? "Esperando escaneo del QR…"
      : "Desconectado";

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
      <h2 className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-slate-700">
        WhatsApp del Connector
        <Ayuda>
          Vincula el número de WhatsApp que usará el Connector (respaldo). Pulsa "Vincular WhatsApp" y
          escanea el QR desde tu teléfono en WhatsApp &gt; Dispositivos vinculados. Mientras no esté
          conectado, el Connector no puede enviar por este número.
        </Ayuda>
      </h2>

      {cargando ? (
        <p className="text-xs text-slate-400">Consultando estado…</p>
      ) : (
        <>
          <div className="mt-2 flex items-center gap-2 text-sm">
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${conectado ? "bg-green-500" : "bg-slate-300"}`}
            />
            <span className="text-slate-700">{etiquetaEstado}</span>
            {estado?.connection_id && (
              <span className="text-xs text-slate-400">({estado.connection_id})</span>
            )}
          </div>

          {!conectado && qr && (
            <div className="mt-4 flex flex-col items-center gap-2">
              <img
                src={qr}
                alt="Código QR de WhatsApp"
                className="h-56 w-56 rounded-lg ring-1 ring-slate-200"
              />
              <p className="text-center text-xs text-slate-500">
                WhatsApp &gt; Dispositivos vinculados &gt; Vincular un dispositivo. El QR se actualiza
                solo.
              </p>
            </div>
          )}

          <div className="mt-4 flex items-center gap-3">
            {conectado ? (
              <button
                type="button"
                onClick={desvincular}
                disabled={accion !== null}
                className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {accion === "desvincular" ? "Desvinculando…" : "Desvincular"}
              </button>
            ) : (
              <button
                type="button"
                onClick={vincular}
                disabled={accion !== null}
                className="rounded-lg bg-[#2563EB] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {accion === "vincular" ? "Generando QR…" : qr ? "Regenerar QR" : "Vincular WhatsApp"}
              </button>
            )}
          </div>

          {msg && <p className="mt-2 text-xs text-red-600">{msg}</p>}
        </>
      )}
    </div>
  );
}
