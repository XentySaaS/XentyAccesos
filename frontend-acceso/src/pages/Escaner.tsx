/**
 * Escáner — pantalla de acceso, integrada al layout normal del panel (sidebar/topbar visibles).
 * Estado: espera → leyendo → {permitido | denegado | advertencia} → espera (confirmación manual
 * del guardia; sin auto-avance, para dar tiempo de cotejar foto/documentos contra la persona).
 * Soporta cámara (por defecto, preferencia guardada), lector HID (teclado) y submit manual.
 */
import { KeyboardEvent, useEffect, useRef, useState } from "react";
import { Html5Qrcode, Html5QrcodeScannerState } from "html5-qrcode";
import api from "../api/client";

const QR_DIV_ID = "qr-reader-camara";
const PREF_CAMARA_KEY = "xenty_escaner_camara";

type Estado = "espera" | "leyendo" | "permitido" | "denegado" | "advertencia";

interface CampoDetalle { label: string; valor: string | number | null; }
interface Detalle { tipo: string; titulo: string; campos: CampoDetalle[]; }
interface Documento { nombre: string; estado: string; url: string; }
interface AccesoHist { tipo_acceso: string; hora_entrada: string; hora_salida: string | null; }

interface Resultado {
  permitido: boolean;
  motivo: string;
  tipo_acceso: string | null;
  registro_id?: number;
  nombre?: string;
  empresa?: string;
  foto_url?: string;
  nota?: string;
  contacto?: { email?: string | null; telefono?: string | null };
  detalle?: Detalle | null;
  documentos?: Documento[];
  historial?: AccesoHist[];
}

export default function Escaner() {
  const [estado,   setEstado]   = useState<Estado>("espera");
  const [qrBuffer, setQrBuffer] = useState("");
  const [resultado,setResultado]= useState<Resultado | null>(null);
  const [turno,    setTurno]    = useState(0);
  const [rechazando, setRechazando] = useState(false);
  const [motivoRechazo, setMotivoRechazo] = useState("");
  const [enviandoRechazo, setEnviandoRechazo] = useState(false);
  const [errorRechazo, setErrorRechazo] = useState<string | null>(null);
  const [modoCamara, setModoCamara] = useState(() => localStorage.getItem(PREF_CAMARA_KEY) !== "0");
  const [errorCamara, setErrorCamara] = useState<string | null>(null);
  const inputRef   = useRef<HTMLInputElement>(null);
  const html5QrRef = useRef<Html5Qrcode | null>(null);
  const procesarRef = useRef<(qr: string) => void>(() => {});

  function alternarCamara() {
    setModoCamara(m => {
      const nuevo = !m;
      localStorage.setItem(PREF_CAMARA_KEY, nuevo ? "1" : "0");
      return nuevo;
    });
  }

  // Foco automático en el input oculto para capturar lector HID
  useEffect(() => { inputRef.current?.focus(); }, [estado]);

  // El div de la cámara solo existe en el DOM mientras se muestra este bloque (espera/leyendo);
  // las pantallas de veredicto lo desmontan. La cámara debe arrancar/pararse junto con ese ciclo
  // de vida — si no, un resume() tras un remonte apuntaría a un nodo <div> ya desechado.
  const camaraMontada = modoCamara && (estado === "espera" || estado === "leyendo");

  useEffect(() => {
    if (!camaraMontada) return;
    const qr = new Html5Qrcode(QR_DIV_ID);
    html5QrRef.current = qr;
    let vivo = true;
    // html5-qrcode lanza excepciones SÍNCRONAS (no promesas rechazadas) al llamar stop()/clear()
    // sobre un scanner que nunca llegó a SCANNING — hay que saberlo con certeza, no adivinar por
    // getState() (que puede leerse a mitad de una transición).
    let iniciado = false;

    // Detiene y limpia solo si de verdad llegó a arrancar; nunca deja escapar una excepción.
    const detenerYLimpiar = () => {
      try {
        qr.stop().catch(() => {}).finally(() => { try { qr.clear(); } catch { /* noop */ } });
      } catch {
        try { qr.clear(); } catch { /* noop */ }
      }
    };

    qr.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 200 },
      decodedText => {
        if (!vivo) return;
        try { qr.pause(true); } catch { /* ya pausado */ }
        procesarRef.current(decodedText);
      },
      () => { /* frame sin QR legible: ignorar */ },
    ).then(() => {
      iniciado = true;
      // Se desmontó mientras la cámara arrancaba (permiso concedido tarde): detenerla ya.
      if (!vivo) detenerYLimpiar();
    }).catch(() => {
      if (!vivo) return;
      setErrorCamara("No se pudo acceder a la cámara. Revisa los permisos del navegador.");
      setModoCamara(false);
    });

    return () => {
      vivo = false;
      html5QrRef.current = null;
      if (iniciado) detenerYLimpiar();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [camaraMontada]);

  // Reanuda la decodificación al volver a "espera" (la pausa ocurre al detectar un QR, en el
  // mismo montaje del video — nunca cruza un ciclo de desmontaje/remontaje del div).
  useEffect(() => {
    const qr = html5QrRef.current;
    if (!qr || !camaraMontada) return;
    try {
      if (estado === "espera" && qr.getState() === Html5QrcodeScannerState.PAUSED) qr.resume();
    } catch { /* estado transitorio del scanner, ignorar */ }
  }, [estado, camaraMontada]);

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
      }
    } catch {
      setResultado({ permitido: false, motivo: "Error de conexión. Intenta de nuevo.", tipo_acceso: null });
      setEstado("denegado");
    }
    setQrBuffer("");
  }
  procesarRef.current = procesar;

  function resetear() {
    setEstado("espera");
    setResultado(null);
    setRechazando(false);
    setMotivoRechazo("");
    setEnviandoRechazo(false);
    setErrorRechazo(null);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  // Captura de lector HID: acumula caracteres y dispara al Enter
  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") { procesar(qrBuffer); }
  }

  function abrirRechazo() {
    setRechazando(true);
  }

  async function confirmarRechazo() {
    if (!resultado?.registro_id || !motivoRechazo.trim() || enviandoRechazo) return;
    setEnviandoRechazo(true);
    setErrorRechazo(null);
    try {
      await api.post(`/api/acceso/registros/${resultado.registro_id}/rechazar/`, {
        motivo: motivoRechazo.trim(),
      });
      resetear();
    } catch {
      setEnviandoRechazo(false);
      setErrorRechazo("No se pudo registrar el rechazo. Intenta de nuevo.");
    }
  }

  return (
    <div
      className="flex flex-col overflow-hidden rounded-2xl"
      style={{
        backgroundColor: "#0F1B2D", fontFamily: "'Hanken Grotesk', sans-serif",
        minHeight: "calc(100vh - 140px)",
      }}
      onClick={() => {
        if (rechazando) return;
        // Los veredictos siempre requieren toque explícito del guardia (sin auto-avance).
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
            <div className="relative flex h-56 w-56 items-center justify-center overflow-hidden rounded-lg">
              {/* Esquinas del marco */}
              {["top-0 left-0", "top-0 right-0", "bottom-0 left-0", "bottom-0 right-0"].map((pos, i) => (
                <span key={i} className={`absolute ${pos} z-10 h-8 w-8`} style={{
                  borderColor: "#60A5FA",
                  borderStyle: "solid",
                  borderWidth: 0,
                  ...(i === 0 ? { borderTopWidth: 3, borderLeftWidth: 3 } : {}),
                  ...(i === 1 ? { borderTopWidth: 3, borderRightWidth: 3 } : {}),
                  ...(i === 2 ? { borderBottomWidth: 3, borderLeftWidth: 3 } : {}),
                  ...(i === 3 ? { borderBottomWidth: 3, borderRightWidth: 3 } : {}),
                }} />
              ))}

              {/* Vista de cámara: montada de forma continua mientras modoCamara esté activo */}
              <div
                id={QR_DIV_ID}
                className="h-full w-full"
                style={{ display: modoCamara ? "block" : "none" }}
              />

              {!modoCamara && (
                estado === "leyendo" ? (
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
                )
              )}

              {/* Overlay de validación sobre el video congelado (pausado al detectar QR) */}
              {modoCamara && estado === "leyendo" && (
                <div
                  className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3"
                  style={{ backgroundColor: "rgba(15,27,45,.85)" }}
                >
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                  <p className="text-sm font-medium" style={{ color: "#93C5FD" }}>Validando…</p>
                </div>
              )}
            </div>

            <div className="text-center">
              <p className="text-lg font-semibold" style={{ color: "#CBD5E1" }}>
                {modoCamara ? "Apunta la cámara al código QR" : "Acerca el gafete al lector"}
              </p>
              <p className="mt-1 text-sm" style={{ color: "#64748B" }}>
                {modoCamara ? "o cambia a lector físico abajo" : "o pega el código QR manualmente abajo"}
              </p>
              {errorCamara && (
                <p className="mt-2 text-sm font-medium" style={{ color: "#FCA5A5" }}>{errorCamara}</p>
              )}
              <button
                onClick={e => {
                  e.stopPropagation();
                  setErrorCamara(null);
                  alternarCamara();
                }}
                className="mt-3 text-xs font-medium underline underline-offset-2"
                style={{ color: "#60A5FA" }}
              >
                {modoCamara ? "Usar lector físico / manual" : "Usar cámara"}
              </button>
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
      {estado === "permitido" && resultado && !rechazando && (
        <div className="relative flex flex-1 flex-col">
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
            nota="Toca para continuar"
            onContinuar={resetear}
            boton="Continuar · siguiente persona"
            ctx={resultado}
          />
          {/* Override del guardia: solo tiene sentido si hay una identidad que cotejar (evento/cita) */}
          {resultado.nombre && resultado.registro_id && (
            <button
              onClick={e => { e.stopPropagation(); abrirRechazo(); }}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs font-medium underline underline-offset-2"
              style={{ color: "rgba(255,255,255,.75)" }}
            >
              ¿No es la persona? Rechazar acceso
            </button>
          )}
        </div>
      )}

      {/* ── RECHAZO (override del guardia) ──────────────────────── */}
      {estado === "permitido" && resultado && rechazando && (
        <div
          className="flex flex-1 flex-col items-center justify-center gap-4 px-8 py-12 text-center"
          style={{ backgroundColor: "#16A34A" }}
          onClick={e => e.stopPropagation()}
        >
          <p className="text-2xl font-extrabold text-white">Rechazar acceso</p>
          <p className="text-sm font-medium" style={{ color: "rgba(255,255,255,.8)" }}>
            {resultado.nombre}{resultado.empresa ? ` · ${resultado.empresa}` : ""}
          </p>
          <textarea
            value={motivoRechazo}
            onChange={e => setMotivoRechazo(e.target.value)}
            placeholder="Motivo del rechazo (obligatorio)…"
            rows={3}
            autoFocus
            className="w-full max-w-sm rounded-lg px-3 py-2 text-sm outline-none"
            style={{ backgroundColor: "rgba(0,0,0,.2)", color: "white", border: "1px solid rgba(255,255,255,.3)" }}
          />
          {errorRechazo && (
            <p className="text-xs font-semibold" style={{ color: "#FEF08A" }}>{errorRechazo}</p>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => setRechazando(false)}
              className="rounded-xl px-6 py-3 text-sm font-bold"
              style={{ backgroundColor: "rgba(255,255,255,.2)", color: "white" }}
            >
              Cancelar
            </button>
            <button
              onClick={confirmarRechazo}
              disabled={!motivoRechazo.trim() || enviandoRechazo}
              className="rounded-xl px-6 py-3 text-sm font-bold disabled:opacity-50"
              style={{ backgroundColor: "rgba(255,255,255,.95)", color: "#DC2626" }}
            >
              {enviandoRechazo ? "Enviando…" : "Confirmar rechazo"}
            </button>
          </div>
        </div>
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
          ctx={resultado}
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
          ctx={resultado}
        />
      )}
    </div>
  );
}

/* ── Veredicto fullscreen ─────────────────────────────────────── */
function fmtFechaHora(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-MX", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function Veredicto({
  color, shadowColor, icono, titulo, nombre, empresa, fotoUrl,
  detalle, nota, onContinuar, boton, ctx,
}: {
  color: string; shadowColor: string;
  icono: React.ReactNode; titulo: string;
  nombre?: string; empresa?: string; fotoUrl?: string;
  detalle: string[]; nota: string;
  onContinuar: () => void; boton: string | null;
  ctx?: Resultado;
}) {
  const [verDetalle, setVerDetalle] = useState(false);
  const [verHistorial, setVerHistorial] = useState(false);
  const stop = (e: React.MouseEvent) => e.stopPropagation();

  const contacto = ctx?.contacto;
  const info = ctx?.detalle;
  const documentos = ctx?.documentos ?? [];
  const historial = ctx?.historial ?? [];

  return (
    <div
      className="flex flex-1 flex-col overflow-y-auto"
      style={{ backgroundColor: color }}
      onClick={onContinuar}
    >
      <div className="m-auto flex w-full flex-col items-center gap-6 px-8 py-12 text-center">
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
            {contacto && (contacto.email || contacto.telefono) && (
              <p className="text-sm" style={{ color: "rgba(255,255,255,.7)" }}>
                {[contacto.email, contacto.telefono].filter(Boolean).join(" · ")}
              </p>
            )}
          </div>
        )}

        {/* Detalle (motivo) */}
        <div
          className="rounded-xl px-6 py-4 text-center"
          style={{ backgroundColor: "rgba(0,0,0,.2)", maxWidth: 420 }}
        >
          {detalle.map((d, i) => (
            <p key={i} className="text-base font-semibold text-white">{d}</p>
          ))}
        </div>

        {/* Documentos requeridos */}
        {documentos.length > 0 && (
          <div className="w-full max-w-md" onClick={stop}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest" style={{ color: "rgba(255,255,255,.7)" }}>
              Documentos
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {documentos.map((d, i) => (
                <a key={i} href={d.url} target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold text-white"
                  style={{ backgroundColor: "rgba(255,255,255,.18)" }}>
                  {d.nombre}
                  <span style={{ color: "rgba(255,255,255,.6)" }}>· {d.estado}</span>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Detalles (colapsable) */}
        {info && info.campos.length > 0 && (
          <div className="w-full max-w-md text-left" onClick={stop}>
            <button
              onClick={() => setVerDetalle(v => !v)}
              className="flex w-full items-center justify-between rounded-lg px-4 py-2.5 text-sm font-semibold text-white"
              style={{ backgroundColor: "rgba(255,255,255,.15)" }}
            >
              <span>Detalles {info.tipo === "cita" ? "de la cita" : info.tipo === "parking" ? "del estacionamiento" : "del evento"}</span>
              <span>{verDetalle ? "▲" : "▼"}</span>
            </button>
            {verDetalle && (
              <div className="mt-1 rounded-lg px-4 py-3" style={{ backgroundColor: "rgba(0,0,0,.2)" }}>
                {info.campos.map((c, i) => (
                  <p key={i} className="py-0.5 text-sm text-white">
                    <span style={{ color: "rgba(255,255,255,.65)" }}>{c.label}: </span>
                    {c.valor === null || c.valor === "" ? "—" : String(c.valor)}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Historial de accesos (colapsable) */}
        {historial.length > 0 && (
          <div className="w-full max-w-md text-left" onClick={stop}>
            <button
              onClick={() => setVerHistorial(v => !v)}
              className="flex w-full items-center justify-between rounded-lg px-4 py-2.5 text-sm font-semibold text-white"
              style={{ backgroundColor: "rgba(255,255,255,.15)" }}
            >
              <span>Historial de accesos ({historial.length})</span>
              <span>{verHistorial ? "▲" : "▼"}</span>
            </button>
            {verHistorial && (
              <ul className="mt-1 rounded-lg px-4 py-3" style={{ backgroundColor: "rgba(0,0,0,.2)" }}>
                {historial.map((h, i) => (
                  <li key={i} className="py-0.5 text-sm text-white">
                    {h.tipo_acceso === "denegado" ? (
                      <><span style={{ color: "#FCA5A5" }}>Denegado</span> · {fmtFechaHora(h.hora_entrada)}</>
                    ) : (
                      <>
                        <span style={{ color: "#86EFAC" }}>E</span> {fmtFechaHora(h.hora_entrada)}
                        {" · "}
                        <span style={{ color: "#FCA5A5" }}>S</span> {h.hora_salida ? fmtFechaHora(h.hora_salida) : "—"}
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

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
