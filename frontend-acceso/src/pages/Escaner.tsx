/**
 * Escáner — pantalla de firma del producto.
 * Modo oscuro a pantalla completa (#0F1B2D).
 * Estado: espera → leyendo → {permitido | denegado | advertencia} → espera (auto 2.5s).
 * Soporta entrada por teclado (lector HID) y submit manual.
 */
import { KeyboardEvent, useEffect, useRef, useState } from "react";
import api from "../api/client";

type Estado = "espera" | "leyendo" | "permitido" | "denegado" | "advertencia";

interface Resultado {
  permitido: boolean;
  motivo: string;
  tipo_acceso: string | null;
  nombre?: string;
  empresa?: string;
  foto_url?: string;
  nota?: string;
}

const AUTO_RESET_MS = 2500;

export default function Escaner() {
  const [estado,   setEstado]   = useState<Estado>("espera");
  const [qrBuffer, setQrBuffer] = useState("");
  const [resultado,setResultado]= useState<Resultado | null>(null);
  const [turno,    setTurno]    = useState(0);
  const inputRef   = useRef<HTMLInputElement>(null);
  const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Foco automático en el input oculto para capturar lector HID
  useEffect(() => { inputRef.current?.focus(); }, [estado]);

  async function procesar(qr: string) {
    if (!qr.trim()) return;
    setEstado("leyendo");
    try {
      const { data } = await api.post<Resultado>("/api/acceso/escanear/", { qr: qr.trim() });
      setResultado(data);
      const nuevo: Estado = data.permitido
        ? (data.nota ? "advertencia" : "permitido")
        : "denegado";
      setEstado(nuevo);
      if (nuevo === "permitido" || nuevo === "advertencia") {
        setTurno(t => t + 1);
        timerRef.current = setTimeout(resetear, AUTO_RESET_MS);
      }
    } catch {
      setResultado({ permitido: false, motivo: "Error de conexión. Intenta de nuevo.", tipo_acceso: null });
      setEstado("denegado");
    }
    setQrBuffer("");
  }

  function resetear() {
    if (timerRef.current) clearTimeout(timerRef.current);
    setEstado("espera");
    setResultado(null);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  // Captura de lector HID: acumula caracteres y dispara al Enter
  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") { procesar(qrBuffer); }
  }

  return (
    <div
      className="fixed inset-0 flex flex-col"
      style={{ backgroundColor: "#0F1B2D", fontFamily: "'Hanken Grotesk', sans-serif" }}
      onClick={() => {
        // Denegado requiere toque explícito; permitido/advertencia auto-regresan pero también aceptan toque
        if (estado === "denegado" || estado === "permitido" || estado === "advertencia") resetear();
        else inputRef.current?.focus();
      }}
    >
      {/* Input oculto para lector HID */}
      <input
        ref={inputRef}
        className="absolute opacity-0 h-0 w-0"
        value={qrBuffer}
        onChange={e => setQrBuffer(e.target.value)}
        onKeyDown={onKeyDown}
        autoFocus
        aria-hidden
      />

      {/* ── ESPERA ──────────────────────────────────────────────── */}
      {(estado === "espera" || estado === "leyendo") && (
        <div className="flex flex-1 flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid #1F3147" }}>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#60A5FA" }}>
                Acceso · Torniquete
              </p>
              <p className="mt-0.5 text-sm font-medium" style={{ color: "#CBD5E1" }}>
                Recinto activo
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-green-400" style={{ boxShadow: "0 0 6px #4ade80" }} />
              <span className="text-xs font-semibold" style={{ color: "#CBD5E1" }}>En línea</span>
            </div>
          </div>

          {/* Visor central */}
          <div className="flex flex-1 flex-col items-center justify-center gap-6 px-8">
            {/* Marco de esquinas */}
            <div className="relative flex h-56 w-56 items-center justify-center">
              {/* Esquinas del marco */}
              {["top-0 left-0", "top-0 right-0", "bottom-0 left-0", "bottom-0 right-0"].map((pos, i) => (
                <span key={i} className={`absolute ${pos} h-8 w-8`} style={{
                  borderColor: "#60A5FA",
                  borderStyle: "solid",
                  borderWidth: 0,
                  ...(i === 0 ? { borderTopWidth: 3, borderLeftWidth: 3 } : {}),
                  ...(i === 1 ? { borderTopWidth: 3, borderRightWidth: 3 } : {}),
                  ...(i === 2 ? { borderBottomWidth: 3, borderLeftWidth: 3 } : {}),
                  ...(i === 3 ? { borderBottomWidth: 3, borderRightWidth: 3 } : {}),
                }} />
              ))}
              {estado === "leyendo" ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                  <p className="text-sm font-medium" style={{ color: "#93C5FD" }}>Validando…</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3 text-center">
                  {/* Ícono QR */}
                  <svg className="h-16 w-16" style={{ color: "#1F3147" }} fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                    <rect x="3" y="3" width="5" height="5" rx="0.5"/>
                    <rect x="16" y="3" width="5" height="5" rx="0.5"/>
                    <rect x="3" y="16" width="5" height="5" rx="0.5"/>
                    <path d="M13 3v5h5M13 13h5v5M13 8v5M8 13H3"/>
                  </svg>
                </div>
              )}
            </div>

            <div className="text-center">
              <p className="text-lg font-semibold" style={{ color: "#CBD5E1" }}>
                Acerca el gafete al lector
              </p>
              <p className="mt-1 text-sm" style={{ color: "#64748B" }}>
                o pega el código QR manualmente abajo
              </p>
            </div>

            {/* Input manual */}
            <form
              onSubmit={e => { e.preventDefault(); procesar(qrBuffer); }}
              className="flex w-full max-w-sm gap-2"
              onClick={e => e.stopPropagation()}
            >
              <input
                value={qrBuffer}
                onChange={e => setQrBuffer(e.target.value)}
                placeholder="Código QR…"
                className="flex-1 rounded-lg px-3 py-2 text-sm font-mono outline-none"
                style={{ backgroundColor: "#1F3147", color: "#CBD5E1", border: "1px solid #2D4A6B" }}
              />
              <button type="submit"
                className="rounded-lg px-4 py-2 text-sm font-semibold text-white"
                style={{ backgroundColor: "#2563EB" }}>
                Validar
              </button>
            </form>
          </div>

          {/* Pie: contador de turno */}
          <div className="flex items-center justify-between px-6 py-4" style={{ borderTop: "1px solid #1F3147" }}>
            <div>
              <p className="text-xs" style={{ color: "#475569" }}>Accesos este turno</p>
              <p className="tabular text-2xl font-extrabold" style={{ color: "#CBD5E1" }}>
                {turno.toLocaleString("es-MX")}
              </p>
            </div>
            <p className="text-xs" style={{ color: "#475569" }}>Toca en cualquier lugar para enfocar el lector</p>
          </div>
        </div>
      )}

      {/* ── PERMITIDO ─────────────────────────────────────────── */}
      {estado === "permitido" && resultado && (
        <Veredicto
          color="#16A34A"
          shadowColor="rgba(22,163,74,.3)"
          icono={<CheckIcon />}
          titulo="PERMITIDO"
          nombre={resultado.nombre}
          empresa={resultado.empresa}
          fotoUrl={resultado.foto_url}
          detalle={[
            resultado.motivo,
          ].filter(Boolean)}
          nota="Se regresa al escáner automáticamente…"
          onContinuar={resetear}
          boton={null}
        />
      )}

      {/* ── DENEGADO ─────────────────────────────────────────── */}
      {estado === "denegado" && resultado && (
        <Veredicto
          color="#DC2626"
          shadowColor="rgba(220,38,38,.3)"
          icono={<XIcon />}
          titulo="DENEGADO"
          nombre={resultado.nombre}
          empresa={resultado.empresa}
          fotoUrl={resultado.foto_url}
          detalle={[resultado.motivo]}
          nota="Toca para continuar"
          onContinuar={resetear}
          boton="Entendido · continuar"
        />
      )}

      {/* ── ADVERTENCIA ──────────────────────────────────────── */}
      {estado === "advertencia" && resultado && (
        <Veredicto
          color="#D97706"
          shadowColor="rgba(217,119,6,.3)"
          icono={<WarnIcon />}
          titulo="ACCESO CON NOTA"
          nombre={resultado.nombre}
          empresa={resultado.empresa}
          fotoUrl={resultado.foto_url}
          detalle={[resultado.motivo, resultado.nota].filter(Boolean) as string[]}
          nota="Se regresa al escáner automáticamente…"
          onContinuar={resetear}
          boton="Permitir el paso"
        />
      )}
    </div>
  );
}

/* ── Veredicto fullscreen ─────────────────────────────────────── */
function Veredicto({
  color, shadowColor, icono, titulo, nombre, empresa, fotoUrl,
  detalle, nota, onContinuar, boton,
}: {
  color: string; shadowColor: string;
  icono: React.ReactNode; titulo: string;
  nombre?: string; empresa?: string; fotoUrl?: string;
  detalle: string[]; nota: string;
  onContinuar: () => void; boton: string | null;
}) {
  return (
    <div
      className="flex flex-1 flex-col items-center justify-center gap-6 px-8 py-12 text-center"
      style={{ backgroundColor: color }}
      onClick={onContinuar}
    >
      {/* Ícono grande */}
      <div
        className="flex h-20 w-20 items-center justify-center rounded-full"
        style={{ backgroundColor: "rgba(255,255,255,.2)", boxShadow: `0 16px 48px ${shadowColor}` }}
      >
        {icono}
      </div>

      {/* Veredicto */}
      <p className="text-[46px] font-extrabold leading-none tracking-tight text-white"
        style={{ letterSpacing: "-.01em" }}>
        {titulo}
      </p>

      {/* Foto + nombre */}
      {(fotoUrl || nombre) && (
        <div className="flex flex-col items-center gap-3">
          {fotoUrl ? (
            <img src={fotoUrl} alt={nombre}
              className="h-24 w-24 rounded-full object-cover"
              style={{ border: "4px solid rgba(255,255,255,.4)" }} />
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-full text-2xl font-bold text-white"
              style={{ backgroundColor: "rgba(255,255,255,.2)" }}>
              {(nombre ?? "?")[0].toUpperCase()}
            </div>
          )}
          {nombre && (
            <p className="text-[26px] font-extrabold text-white">{nombre}</p>
          )}
          {empresa && (
            <p className="text-base font-medium" style={{ color: "rgba(255,255,255,.8)" }}>{empresa}</p>
          )}
        </div>
      )}

      {/* Detalle */}
      <div
        className="rounded-xl px-6 py-4 text-center"
        style={{ backgroundColor: "rgba(0,0,0,.2)", maxWidth: 420 }}
      >
        {detalle.map((d, i) => (
          <p key={i} className="text-base font-semibold text-white">{d}</p>
        ))}
      </div>

      {/* Nota / botón */}
      {boton ? (
        <button
          onClick={e => { e.stopPropagation(); onContinuar(); }}
          className="rounded-xl px-8 py-3 text-base font-bold transition hover:opacity-90"
          style={{ backgroundColor: "rgba(255,255,255,.95)", color }}
        >
          {boton}
        </button>
      ) : (
        <p className="text-sm font-medium" style={{ color: "rgba(255,255,255,.7)" }}>{nota}</p>
      )}
    </div>
  );
}

function CheckIcon() {
  return (
    <svg className="h-10 w-10 text-white" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
      <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
function XIcon() {
  return (
    <svg className="h-10 w-10 text-white" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
      <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
function WarnIcon() {
  return (
    <svg className="h-10 w-10 text-white" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}
