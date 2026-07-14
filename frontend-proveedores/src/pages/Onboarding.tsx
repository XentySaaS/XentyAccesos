import axios from "axios";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const INK    = "#0F1B2D";
const SIGNAL = "#2563EB";

const http = axios.create({ baseURL: "/" });

// ── Tipos ──────────────────────────────────────────────────────────────────
type StepId = 1 | 2 | 3;

interface FormState {
  nombre: string; razon_social: string; rfc: string;
  email_empresa: string; telefono_empresa: string;
  repse: File | null; sua: File | null;
  nombre_resp: string; apellidos: string; puesto: string;
  email: string; curp: string; nss: string; whatsapp: string;
  file_ine: File | null; foto: File | null;
  password: string; confirmar: string;
  privacy: boolean; terms: boolean;
}

const INIT: FormState = {
  nombre: "", razon_social: "", rfc: "",
  email_empresa: "", telefono_empresa: "",
  repse: null, sua: null,
  nombre_resp: "", apellidos: "", puesto: "",
  email: "", curp: "", nss: "", whatsapp: "",
  file_ine: null, foto: null,
  password: "", confirmar: "",
  privacy: false, terms: false,
};

const STEPS: { id: StepId; label: string }[] = [
  { id: 1, label: "Empresa" },
  { id: 2, label: "Responsable" },
  { id: 3, label: "Acceso" },
];

// ── Helpers de estilo ──────────────────────────────────────────────────────
const inp  = (err?: string) =>
  `w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:ring-2 ${
    err
      ? "border-red-300 focus:border-red-400 focus:ring-red-100"
      : "border-slate-200 focus:border-blue-400 focus:ring-blue-100"
  }`;

function Lbl({ children, req }: { children: React.ReactNode; req?: boolean }) {
  return (
    <span className="mb-1 block text-xs font-semibold text-slate-600">
      {children}{req && <span className="ml-0.5 text-red-500">*</span>}
    </span>
  );
}
function Err({ msg }: { msg?: string }) {
  return msg ? <p className="mt-1 text-[11px] text-red-500">{msg}</p> : null;
}

// ── Subida de archivos ─────────────────────────────────────────────────────
function FileZone({
  label, accept, file, onChange, hint, req, error,
}: {
  label: string; accept: string; file: File | null;
  onChange: (f: File | null) => void; hint?: string; req?: boolean; error?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div>
      {label && <Lbl req={req}>{label}</Lbl>}
      <div
        role="button" tabIndex={0}
        onClick={() => ref.current?.click()}
        onKeyDown={e => e.key === "Enter" && ref.current?.click()}
        className={`flex min-h-[64px] cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed px-4 py-3 transition hover:border-blue-300 ${
          file
            ? "border-green-400 bg-green-50"
            : error
            ? "border-red-300 bg-red-50"
            : "border-slate-200 bg-slate-50 hover:bg-blue-50/50"
        }`}
      >
        {file ? (
          <>
            <svg className="h-5 w-5 flex-shrink-0 text-green-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>
            <span className="min-w-0 flex-1 truncate text-xs font-medium text-green-700">{file.name}</span>
            <button
              type="button"
              onClick={e => { e.stopPropagation(); onChange(null); if (ref.current) ref.current.value = ""; }}
              className="rounded p-0.5 text-slate-400 hover:text-red-500"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </>
        ) : (
          <>
            <svg className="h-5 w-5 flex-shrink-0 text-slate-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path d="M12 16V8m0 0l-3 3m3-3l3 3M20 16.5A3.5 3.5 0 0016.5 13H15a5 5 0 10-9.9 1M4 16.5A3.5 3.5 0 007.5 20h9"/>
            </svg>
            <span className="text-xs text-slate-400">{hint ?? "Haz clic para seleccionar"}</span>
          </>
        )}
      </div>
      <input ref={ref} type="file" accept={accept} className="hidden"
        onChange={e => onChange(e.target.files?.[0] ?? null)} />
      <Err msg={error} />
    </div>
  );
}

// ── Captura / OCR de INE ──────────────────────────────────────────────────
interface OcrData {
  nombre?: string; apellidos?: string; curp?: string;
  fecha_nacimiento?: string; sexo?: string; domicilio?: string;
}

// Intenta obtener stream con constraints en cascada (iOS Safari + Android Chrome)
async function startCameraStream(): Promise<MediaStream> {
  const constraints: MediaStreamConstraints[] = [
    { video: { facingMode: "environment" } },                          // iOS 14+ + Android
    { video: { facingMode: { ideal: "environment" } } },               // algunos Android
    { video: true },                                                    // cámara frontal / única
  ];
  let lastErr: Error = new Error("sin cámara");
  for (const c of constraints) {
    try { return await navigator.mediaDevices.getUserMedia(c); }
    catch (e) {
      lastErr = e as Error;
      // "NotAllowedError" = permiso denegado; no tiene sentido reintentar
      if ((e as Error).name === "NotAllowedError") throw e;
    }
  }
  throw lastErr;
}

// toBlob con fallback vía toDataURL (iOS < 15 no soporta toBlob)
function canvasToFile(canvas: HTMLCanvasElement): Promise<File> {
  return new Promise((resolve, reject) => {
    const finish = (blob: Blob | null) => {
      if (!blob) return reject(new Error("snapshot fallido"));
      resolve(new File([blob], "ine-captura.jpg", { type: "image/jpeg" }));
    };
    if (typeof canvas.toBlob === "function") {
      canvas.toBlob(finish, "image/jpeg", 0.92);
    } else {
      // Fallback: toDataURL → Blob manual
      const [head, data] = canvas.toDataURL("image/jpeg", 0.92).split(",");
      const mime = head.match(/:(.*?);/)![1];
      const raw  = atob(data);
      const u8   = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) u8[i] = raw.charCodeAt(i);
      finish(new Blob([u8], { type: mime }));
    }
  });
}

const cameraSupported: boolean =
  typeof navigator !== "undefined" &&
  !!navigator.mediaDevices?.getUserMedia;

function IneCaptura({
  file, onFile, onExtracted, error,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
  onExtracted: (d: OcrData) => void;
  error?: string;
}) {
  const [tab,        setTab]       = useState<"subir" | "camara">("subir");
  const [extracting, setExtracting] = useState(false);
  const [ocrResult,  setOcrResult]  = useState<OcrData | null>(null);
  const [ocrError,   setOcrError]   = useState<string | null>(null);
  const [captured,   setCaptured]   = useState<{ src: string; file: File } | null>(null);
  const [camError,   setCamError]   = useState<string | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);

  const videoRef    = useRef<HTMLVideoElement>(null);
  const canvasRef   = useRef<HTMLCanvasElement>(null);
  const streamRef   = useRef<MediaStream | null>(null);

  // Limpiar URL de objeto al desmontar
  useEffect(() => {
    return () => {
      if (previewSrc) URL.revokeObjectURL(previewSrc);
      streamRef.current?.getTracks().forEach(t => t.stop());
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Iniciar / detener cámara al cambiar tab
  useEffect(() => {
    if (tab !== "camara") {
      streamRef.current?.getTracks().forEach(t => t.stop());
      streamRef.current = null;
      setCaptured(null);
      setCamError(null);
      return;
    }

    let active = true;
    startCameraStream()
      .then(s => {
        if (!active) { s.getTracks().forEach(t => t.stop()); return; }
        streamRef.current = s;
        const vid = videoRef.current;
        if (vid) {
          vid.srcObject = s;
          vid.play().catch(() => {}); // iOS Safari a veces requiere play() explícito
        }
      })
      .catch(e => {
        if (!active) return;
        const msg = (e as Error).name === "NotAllowedError"
          ? "Permiso de cámara denegado. Revisa la configuración del navegador."
          : "No se pudo acceder a la cámara. Usa la opción de subir imagen.";
        setCamError(msg);
      });

    return () => {
      active = false;
      streamRef.current?.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    };
  }, [tab]);

  function capturar() {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !streamRef.current) return;

    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d")?.drawImage(video, 0, 0);

    canvasToFile(canvas).then(f => {
      const src = URL.createObjectURL(f);
      setCaptured({ src, file: f });
      onFile(f);
      // Apagar cámara tras capturar (ahorra batería)
      streamRef.current?.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }).catch(() => setCamError("No se pudo guardar la foto."));
  }

  function retomar() {
    if (captured) URL.revokeObjectURL(captured.src);
    setCaptured(null);
    setOcrResult(null);
    setOcrError(null);
    onFile(null);
    setCamError(null);
    let active = true;
    startCameraStream()
      .then(s => {
        if (!active) { s.getTracks().forEach(t => t.stop()); return; }
        streamRef.current = s;
        const vid = videoRef.current;
        if (vid) { vid.srcObject = s; vid.play().catch(() => {}); }
      })
      .catch(e => {
        if (!active) return;
        setCamError((e as Error).name === "NotAllowedError"
          ? "Permiso denegado."
          : "No se pudo reiniciar la cámara.");
      });
    return () => { active = false; };
  }

  async function extraer(imgFile: File) {
    setExtracting(true);
    setOcrError(null);
    setOcrResult(null);
    try {
      const fd = new FormData();
      fd.append("imagen", imgFile);
      const { data } = await http.post<OcrData>("/api/ocr/ine/", fd);
      setOcrResult(data);
      onExtracted(data);
    } catch (err: any) {
      setOcrError(err?.response?.data?.detail ?? "No se pudo leer la imagen. Ingresa los datos manualmente.");
    } finally {
      setExtracting(false);
    }
  }

  function onFileChange(f: File | null) {
    setOcrResult(null);
    setOcrError(null);
    if (previewSrc) URL.revokeObjectURL(previewSrc);
    setPreviewSrc(f ? URL.createObjectURL(f) : null);
    onFile(f);
  }

  const btnExtraer = (imgFile: File) => (
    <button
      type="button"
      onClick={() => extraer(imgFile)}
      disabled={extracting}
      className="flex w-full items-center justify-center gap-2 rounded-xl border border-blue-200 bg-blue-50 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-100 disabled:opacity-50"
    >
      {extracting ? (
        <>
          <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeOpacity={.3} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/><path d="M21 12a9 9 0 00-9-9"/>
          </svg>
          Extrayendo datos…
        </>
      ) : (
        <>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M15 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7l-5-5z"/><path d="M14 2v5h5M10 13l2 2 4-4"/>
          </svg>
          Extraer datos del INE
        </>
      )}
    </button>
  );

  return (
    <div>
      <Lbl req>Identificación oficial (INE/IFE)</Lbl>

      {/* Tabs */}
      <div className="mb-3 flex rounded-xl border border-slate-200 bg-slate-50 p-1 gap-1">
        {(["subir", ...(cameraSupported ? ["camara"] : [])] as ("subir" | "camara")[]).map(t => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition ${
              tab === t
                ? "bg-white shadow-sm text-blue-600 ring-1 ring-slate-200"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "subir" ? (
              <>
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M12 16V8m0 0l-3 3m3-3l3 3M20 16.5A3.5 3.5 0 0016.5 13H15a5 5 0 10-9.9 1M4 16.5A3.5 3.5 0 007.5 20h9"/>
                </svg>
                Subir imagen
              </>
            ) : (
              <>
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <circle cx="12" cy="13" r="3"/><path d="M20.04 7.32A2 2 0 0018.16 6H5.84A2 2 0 003.96 7.32L2 10v10a2 2 0 002 2h16a2 2 0 002-2V10l-1.96-2.68z"/>
                </svg>
                Tomar foto
              </>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab: Subir imagen ── */}
      {tab === "subir" && (
        <div className="space-y-3">
          <FileZone
            label="" accept=".jpg,.jpeg,.png,.pdf"
            file={file}
            onChange={onFileChange}
            hint="Foto o escaneo del INE · JPG / PNG / PDF · máx. 10 MB"
            error={error}
          />
          {previewSrc && (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
              <img src={previewSrc} alt="Vista previa INE" className="max-h-52 w-full object-contain" />
            </div>
          )}
          {file && !ocrResult && btnExtraer(file)}
        </div>
      )}

      {/* ── Tab: Tomar foto ── */}
      {tab === "camara" && (
        <div className="space-y-3">
          {camError ? (
            <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{camError}</div>
          ) : captured ? (
            <>
              <div className="overflow-hidden rounded-xl border border-green-200 bg-green-50">
                <img src={captured.src} alt="Foto capturada" className="max-h-52 w-full object-contain" />
              </div>
              <button type="button" onClick={retomar}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50">
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M1 4v6h6"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
                </svg>
                Retomar foto
              </button>
              {!ocrResult && btnExtraer(captured.file)}
            </>
          ) : (
            <>
              <div className="overflow-hidden rounded-xl bg-black">
                <video ref={videoRef} autoPlay playsInline muted
                  className="max-h-52 w-full object-cover" />
              </div>
              <button type="button" onClick={capturar}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <circle cx="12" cy="13" r="3"/><path d="M20.04 7.32A2 2 0 0018.16 6H5.84A2 2 0 003.96 7.32L2 10v10a2 2 0 002 2h16a2 2 0 002-2V10l-1.96-2.68z"/>
                </svg>
                Capturar foto
              </button>
            </>
          )}
          <canvas ref={canvasRef} className="hidden" />
        </div>
      )}

      {/* ── Banner OCR resultado ── */}
      {ocrResult && (
        <div className="mt-3 rounded-xl border border-green-200 bg-green-50 px-4 py-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-bold text-green-700">
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>
            Datos extraídos del INE
          </p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-green-800">
            {ocrResult.nombre         && <span><span className="font-semibold">Nombre:</span> {ocrResult.nombre}</span>}
            {ocrResult.apellidos      && <span><span className="font-semibold">Apellidos:</span> {ocrResult.apellidos}</span>}
            {ocrResult.curp           && <span><span className="font-semibold">CURP:</span> {ocrResult.curp}</span>}
            {ocrResult.fecha_nacimiento && <span><span className="font-semibold">Nacimiento:</span> {ocrResult.fecha_nacimiento}</span>}
          </div>
          <p className="mt-2 text-[11px] text-green-600">Los campos se llenaron automáticamente — revísalos antes de continuar.</p>
        </div>
      )}

      {/* ── Banner error OCR (no fatal) ── */}
      {ocrError && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-700">
          <span className="font-semibold">No se pudo leer la imagen:</span> {ocrError}
        </div>
      )}
    </div>
  );
}

// ── Stepper ────────────────────────────────────────────────────────────────
function Stepper({ step }: { step: StepId }) {
  const pct = ((step - 1) / (STEPS.length - 1)) * 100;
  return (
    <div className="relative mb-8 px-4">
      <div className="absolute left-[calc(50%/3+16px)] right-[calc(50%/3+16px)] top-4 h-0.5 bg-slate-200" />
      <div
        className="absolute left-[calc(50%/3+16px)] top-4 h-0.5 bg-blue-500 transition-all duration-300"
        style={{ width: `calc((100% - calc(100%/3+32px)) * ${pct / 100})` }}
      />
      <div className="relative flex justify-between">
        {STEPS.map(s => {
          const done   = step > s.id;
          const active = step === s.id;
          return (
            <div key={s.id} className="flex flex-col items-center gap-2" style={{ width: "33.33%" }}>
              <div className={`relative z-10 flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-bold transition-all ${
                active ? "border-blue-500 bg-blue-500 text-white shadow-md shadow-blue-200"
                : done  ? "border-green-500 bg-green-500 text-white"
                        : "border-slate-300 bg-white text-slate-400"
              }`}>
                {done
                  ? <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>
                  : s.id
                }
              </div>
              <span className={`text-xs font-semibold ${
                active ? "text-blue-600" : done ? "text-green-600" : "text-slate-400"
              }`}>{s.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Componente principal ───────────────────────────────────────────────────
export default function Onboarding() {
  const [params]   = useSearchParams();
  const navigate   = useNavigate();
  const token      = params.get("token") ?? "";

  const [step,        setStep]       = useState<StepId>(1);
  const [form,        setForm]       = useState<FormState>(INIT);
  const [errs,        setErrs]       = useState<Partial<Record<keyof FormState | "general", string>>>({});
  const [saving,      setSaving]     = useState(false);
  const [loading,     setLoading]    = useState(true);
  const [tokenErr,    setTokenErr]   = useState<string | null>(null);
  const [yaRegistrado, setYaRegistrado] = useState(false);
  const [success,     setSuccess]    = useState(false);
  // Modal de documentos legales (aviso / términos) leídos desde el backend por token.
  const [docModal,   setDocModal]   = useState<{ tipo: string; titulo: string } | null>(null);
  const [docTexto,   setDocTexto]   = useState("");
  const [docLoading, setDocLoading] = useState(false);
  const [docError,   setDocError]   = useState<string | null>(null);

  async function abrirDoc(tipo: string, titulo: string) {
    setDocModal({ tipo, titulo });
    setDocTexto("");
    setDocError(null);
    setDocLoading(true);
    try {
      const { data } = await http.get<{ texto: string }>(
        `/api/onboarding/documento/?token=${encodeURIComponent(token)}&tipo=${tipo}`,
      );
      setDocTexto(data.texto || "");
    } catch (err: any) {
      setDocError(
        err?.response?.status === 404
          ? "Este documento aún no ha sido publicado por el recinto. Consúltalo con el administrador."
          : "No se pudo cargar el documento.",
      );
    } finally {
      setDocLoading(false);
    }
  }

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    http.get(`/api/onboarding/proveedor/?token=${encodeURIComponent(token)}`)
      .then(({ data }) => {
        setForm(f => ({
          ...f,
          nombre:           data.nombre           ?? "",
          razon_social:     data.razon_social      ?? "",
          rfc:              data.rfc               ?? "",
          email_empresa:    data.email_empresa     ?? "",
          telefono_empresa: data.telefono_empresa  ?? "",
          nombre_resp:      data.nombre_responsable
            ? data.nombre_responsable.split(" ")[0] : "",
          email:            data.email_responsable ?? "",
        }));
      })
      .catch(err => {
        const st     = err?.response?.status;
        const detail = err?.response?.data?.detail ?? "";
        const yaReg  = !!err?.response?.data?.ya_registrado;
        if (yaReg) { setYaRegistrado(true); return; }
        const fatal  =
          (st === 400 && (detail.includes("expiró") || detail.includes("inválid"))) ||
          st === 404;
        if (fatal) setTokenErr(detail || "Invitación inválida o expirada.");
      })
      .finally(() => setLoading(false));
  }, [token]);

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm(f => ({ ...f, [k]: v }));
  const clr = (k: keyof FormState) =>
    setErrs(e => { const n = { ...e }; delete n[k]; return n; });

  function validate(s: StepId): boolean {
    const e: typeof errs = {};
    if (s === 1) {
      if (!form.nombre.trim())           e.nombre           = "Requerido";
      if (!form.razon_social.trim())     e.razon_social     = "Requerido";
      if (!form.telefono_empresa.trim()) e.telefono_empresa = "Requerido";
      else if (!/^\d{10}$/.test(form.telefono_empresa)) e.telefono_empresa = "Debe tener 10 dígitos";
      if (form.rfc && !/^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$/i.test(form.rfc))
        e.rfc = "Formato inválido";
      if (!form.repse) e.repse = "Sube el documento REPSE";
      if (!form.sua)   e.sua   = "Sube el documento SUA";
    }
    if (s === 2) {
      if (!form.nombre_resp.trim()) e.nombre_resp = "Requerido";
      if (!form.apellidos.trim())   e.apellidos   = "Requerido";
      if (!form.puesto.trim())      e.puesto      = "Requerido";
      if (!form.email.trim())       e.email       = "Requerido";
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Correo inválido";
      if (form.curp && form.curp.length !== 18) e.curp = "Debe tener 18 caracteres";
      if (form.nss && !/^\d{11}$/.test(form.nss)) e.nss = "Debe ser 11 dígitos";
      if (!form.whatsapp.trim())    e.whatsapp    = "Requerido";
      else if (!/^\d{10}$/.test(form.whatsapp)) e.whatsapp = "Debe tener 10 dígitos";
      if (!form.file_ine)           e.file_ine    = "Sube o toma foto del INE";
    }
    if (s === 3) {
      if (!form.password)                   e.password  = "Requerido";
      else if (form.password.length < 8)    e.password  = "Mínimo 8 caracteres";
      if (form.password !== form.confirmar) e.confirmar = "Las contraseñas no coinciden";
      if (!form.privacy)                    e.privacy   = "Debes aceptar el Aviso de Privacidad";
      if (!form.terms)                      e.terms     = "Debes aceptar los Términos y Condiciones";
    }
    setErrs(e);
    return Object.keys(e).length === 0;
  }

  function next() { if (validate(step) && step < 3) setStep((step + 1) as StepId); }
  function prev() { if (step > 1) setStep((step - 1) as StepId); }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!validate(3)) return;
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append("token",            token);
      fd.append("email_empresa",    form.email_empresa);
      fd.append("telefono_empresa", form.telefono_empresa);
      if (form.repse)    fd.append("repse",    form.repse);
      if (form.sua)      fd.append("sua",      form.sua);
      fd.append("nombre",    form.nombre_resp);
      fd.append("apellidos", form.apellidos);
      fd.append("puesto",    form.puesto);
      fd.append("email",     form.email);
      fd.append("curp",      form.curp);
      fd.append("nss",       form.nss);
      fd.append("whatsapp",  form.whatsapp);
      if (form.file_ine) fd.append("file_ine", form.file_ine);
      if (form.foto)     fd.append("foto",     form.foto);
      fd.append("password", form.password);
      fd.append("privacy",  String(form.privacy));
      fd.append("terms",    String(form.terms));
      await http.post("/api/onboarding/proveedor/", fd);
      setSuccess(true);
    } catch (err: any) {
      const d = err?.response?.data;
      if (d && typeof d === "object") {
        const mapped: typeof errs = {};
        for (const [k, v] of Object.entries(d)) {
          mapped[k as keyof FormState] = (Array.isArray(v) ? v[0] : v) as string;
        }
        setErrs(mapped);
        const s1: (keyof FormState)[] = ["nombre", "rfc", "repse", "sua"];
        const s2: (keyof FormState)[] = ["email", "curp", "nss", "file_ine"];
        if (s1.some(k => mapped[k])) setStep(1);
        else if (s2.some(k => mapped[k])) setStep(2);
      } else {
        setErrs({ general: d?.detail ?? "Error al enviar." });
      }
    } finally { setSaving(false); }
  }

  // ── Pantallas especiales ──────────────────────────────────────────────────
  if (yaRegistrado) {
    return (
      <Scaffold>
        <div className="mx-auto w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-xl">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-blue-50">
            <svg className="h-7 w-7 text-blue-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
            </svg>
          </div>
          <h1 className="mb-2 text-lg font-bold" style={{ color: INK }}>Registro ya completado</h1>
          <p className="mb-6 text-sm text-slate-500">
            Esta invitación ya fue utilizada. Si aún no tienes acceso, contacta al administrador del recinto.
          </p>
          <button onClick={() => navigate("/")}
            className="w-full rounded-xl py-2.5 text-sm font-semibold text-white transition hover:opacity-90"
            style={{ backgroundColor: SIGNAL }}>
            Ir al inicio de sesión
          </button>
        </div>
      </Scaffold>
    );
  }

  if (!token || tokenErr) {
    return (
      <Scaffold>
        <div className="mx-auto w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-xl">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-50">
            <svg className="h-7 w-7 text-red-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
            </svg>
          </div>
          <h1 className="mb-2 text-lg font-bold" style={{ color: INK }}>Link inválido</h1>
          <p className="text-sm text-slate-500">
            {tokenErr ?? "Este link no es válido. Solicita una nueva invitación."}
          </p>
        </div>
      </Scaffold>
    );
  }

  if (loading) {
    return (
      <Scaffold>
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <span className="text-sm text-slate-500">Cargando tu invitación…</span>
        </div>
      </Scaffold>
    );
  }

  if (success) {
    return (
      <Scaffold>
        <div className="mx-auto w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-xl">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-50">
            <svg className="h-7 w-7 text-green-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>
          </div>
          <h1 className="mb-2 text-xl font-bold" style={{ color: INK }}>¡Registro completado!</h1>
          <p className="mb-6 text-sm text-slate-500">
            Tu empresa fue registrada como proveedor. El administrador revisará tus documentos y activará tu acceso.
            Recibirás un correo cuando estés activo.
          </p>
          <button onClick={() => navigate("/")}
            className="w-full rounded-xl py-2.5 text-sm font-semibold text-white transition hover:opacity-90"
            style={{ backgroundColor: SIGNAL }}>
            Ir al inicio de sesión
          </button>
        </div>
      </Scaffold>
    );
  }

  // ── Wizard ────────────────────────────────────────────────────────────────
  return (
    <Scaffold>
      <div className="mx-auto w-full max-w-[680px]">

        {/* Encabezado */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-2xl shadow-lg" style={{ backgroundColor: SIGNAL }}>
            <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path d="M20 7H4a2 2 0 00-2 2v6a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z"/>
              <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/>
            </svg>
          </div>
          <h1 className="text-[22px] font-extrabold tracking-tight" style={{ color: INK }}>
            Completa tu registro como proveedor
          </h1>
          {form.nombre && (
            <p className="mt-1 text-sm text-slate-500">
              <span className="font-semibold text-slate-700">{form.nombre}</span>
              {" — "}sigue los pasos para activar tu cuenta.
            </p>
          )}
        </div>

        {/* Stepper */}
        <Stepper step={step} />

        {/* Formulario */}
        <form onSubmit={enviar}>
          <div className="rounded-2xl bg-white px-6 py-6 shadow-lg ring-1 ring-slate-100">

            {errs.general && (
              <div className="mb-4 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">
                {errs.general}
              </div>
            )}

            {/* ── Paso 1: Empresa ──────────────────────────────────────── */}
            {step === 1 && (
              <div className="space-y-4">
                <SectionTitle>Datos de la empresa</SectionTitle>
                <label className="block">
                  <Lbl req>Nombre de la empresa</Lbl>
                  <input value={form.nombre} className={inp(errs.nombre)}
                    onChange={e => { set("nombre", e.target.value); clr("nombre"); }} />
                  <Err msg={errs.nombre} />
                </label>

                <label className="block">
                  <Lbl req>Razón social</Lbl>
                  <input value={form.razon_social} className={inp(errs.razon_social)}
                    onChange={e => { set("razon_social", e.target.value); clr("razon_social"); }} />
                  <Err msg={errs.razon_social} />
                </label>

                <div className="grid grid-cols-2 gap-4">
                  <label className="block">
                    <Lbl>RFC</Lbl>
                    <input value={form.rfc} maxLength={13} placeholder="AAA010101XXX"
                      className={`${inp(errs.rfc)} font-mono uppercase`}
                      onChange={e => { set("rfc", e.target.value.toUpperCase()); clr("rfc"); }} />
                    <Err msg={errs.rfc} />
                  </label>
                  <label className="block">
                    <Lbl req>Teléfono</Lbl>
                    <input value={form.telefono_empresa} placeholder="5512345678" maxLength={10} inputMode="numeric"
                      className={inp(errs.telefono_empresa)}
                      onChange={e => { set("telefono_empresa", e.target.value.replace(/\D/g, "").slice(0, 10)); clr("telefono_empresa"); }} />
                    <Err msg={errs.telefono_empresa} />
                  </label>
                </div>

                <label className="block">
                  <Lbl>Correo electrónico de la empresa</Lbl>
                  <input type="email" value={form.email_empresa}
                    className={inp(errs.email_empresa)}
                    onChange={e => { set("email_empresa", e.target.value); clr("email_empresa"); }} />
                  <Err msg={errs.email_empresa} />
                </label>

                <SectionTitle>Documentos</SectionTitle>
                <div className="grid grid-cols-2 gap-4">
                  <FileZone label="Documento REPSE" accept=".pdf,.jpg,.jpeg,.png" req
                    file={form.repse} onChange={f => { set("repse", f); clr("repse"); }}
                    hint="PDF o imagen · máx. 10 MB" error={errs.repse} />
                  <FileZone label="Documento SUA" accept=".pdf,.jpg,.jpeg,.png" req
                    file={form.sua} onChange={f => { set("sua", f); clr("sua"); }}
                    hint="PDF o imagen · máx. 10 MB" error={errs.sua} />
                </div>
              </div>
            )}

            {/* ── Paso 2: Responsable ──────────────────────────────────── */}
            {step === 2 && (
              <div className="space-y-4">
                <SectionTitle>Datos del responsable</SectionTitle>
                <div className="grid grid-cols-2 gap-4">
                  <label className="block">
                    <Lbl req>Nombre(s)</Lbl>
                    <input value={form.nombre_resp} className={inp(errs.nombre_resp)}
                      onChange={e => { set("nombre_resp", e.target.value); clr("nombre_resp"); }} />
                    <Err msg={errs.nombre_resp} />
                  </label>
                  <label className="block">
                    <Lbl req>Apellidos</Lbl>
                    <input value={form.apellidos} className={inp(errs.apellidos)}
                      onChange={e => { set("apellidos", e.target.value); clr("apellidos"); }} />
                    <Err msg={errs.apellidos} />
                  </label>
                  <label className="block">
                    <Lbl req>Puesto</Lbl>
                    <input value={form.puesto} placeholder="Ej. Director General"
                      className={inp(errs.puesto)}
                      onChange={e => { set("puesto", e.target.value); clr("puesto"); }} />
                    <Err msg={errs.puesto} />
                  </label>
                  <label className="block">
                    <Lbl req>WhatsApp</Lbl>
                    <input value={form.whatsapp} placeholder="5512345678" maxLength={10} inputMode="numeric"
                      className={inp(errs.whatsapp)}
                      onChange={e => { set("whatsapp", e.target.value.replace(/\D/g, "").slice(0, 10)); clr("whatsapp"); }} />
                    <Err msg={errs.whatsapp} />
                  </label>
                </div>

                <label className="block">
                  <Lbl req>Correo electrónico (será tu usuario de acceso)</Lbl>
                  <input type="email" value={form.email} className={inp(errs.email)}
                    onChange={e => { set("email", e.target.value); clr("email"); }} />
                  <Err msg={errs.email} />
                </label>

                <div className="grid grid-cols-2 gap-4">
                  <label className="block">
                    <Lbl>CURP</Lbl>
                    <input value={form.curp} maxLength={18} placeholder="XEXX010101HNEXXXA4"
                      className={`${inp(errs.curp)} font-mono uppercase`}
                      onChange={e => { set("curp", e.target.value.toUpperCase()); clr("curp"); }} />
                    <Err msg={errs.curp} />
                  </label>
                  <label className="block">
                    <Lbl>NSS</Lbl>
                    <input value={form.nss} maxLength={11} placeholder="12345678901"
                      className={`${inp(errs.nss)} font-mono`}
                      onChange={e => { set("nss", e.target.value.replace(/\D/g, "")); clr("nss"); }} />
                    <Err msg={errs.nss} />
                  </label>
                </div>

                <SectionTitle>Documentos del responsable</SectionTitle>

                {/* Escáner OCR de INE */}
                <IneCaptura
                  file={form.file_ine}
                  onFile={f => { set("file_ine", f); clr("file_ine"); }}
                  onExtracted={d => {
                    if (d.nombre)    { set("nombre_resp", d.nombre);            clr("nombre_resp"); }
                    if (d.apellidos) { set("apellidos",   d.apellidos);          clr("apellidos"); }
                    if (d.curp)      { set("curp",        d.curp.toUpperCase()); clr("curp"); }
                  }}
                  error={errs.file_ine}
                />

                <FileZone label="Foto del responsable" accept=".jpg,.jpeg,.png"
                  file={form.foto} onChange={f => set("foto", f)}
                  hint="JPG o PNG · máx. 5 MB" />
              </div>
            )}

            {/* ── Paso 3: Acceso ───────────────────────────────────────── */}
            {step === 3 && (
              <div className="space-y-4">
                <SectionTitle>Crea tu contraseña</SectionTitle>
                <div className="grid grid-cols-2 gap-4">
                  <label className="block">
                    <Lbl req>Contraseña</Lbl>
                    <input type="password" minLength={8} value={form.password}
                      className={inp(errs.password)}
                      onChange={e => { set("password", e.target.value); clr("password"); }} />
                    <Err msg={errs.password} />
                  </label>
                  <label className="block">
                    <Lbl req>Confirmar contraseña</Lbl>
                    <input type="password" minLength={8} value={form.confirmar}
                      className={inp(errs.confirmar)}
                      onChange={e => { set("confirmar", e.target.value); clr("confirmar"); }} />
                    <Err msg={errs.confirmar} />
                  </label>
                </div>

                {/* Resumen */}
                <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm space-y-1 ring-1 ring-slate-100">
                  <p className="font-semibold text-slate-700 mb-1">Resumen de tu registro</p>
                  <p className="text-slate-500"><span className="font-medium text-slate-700">Empresa:</span> {form.nombre}</p>
                  <p className="text-slate-500"><span className="font-medium text-slate-700">Responsable:</span> {form.nombre_resp} {form.apellidos}</p>
                  <p className="text-slate-500"><span className="font-medium text-slate-700">Correo de acceso:</span> {form.email}</p>
                </div>

                <SectionTitle>Consentimiento</SectionTitle>
                <div className="space-y-3">
                  {[
                    { k: "privacy" as const, prefix: "Acepto el ", link: "Aviso de Privacidad", tipo: "aviso_privacidad" },
                    { k: "terms"   as const, prefix: "Acepto los ", link: "Términos y Condiciones", tipo: "terminos_condiciones" },
                  ].map(({ k, prefix, link, tipo }) => (
                    <div key={k}>
                      <div className="flex items-start gap-3">
                        <input id={`chk-${k}`} type="checkbox" checked={form[k] as boolean}
                          onChange={e => { set(k, e.target.checked); clr(k); }}
                          className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border-slate-300 accent-blue-600" />
                        <span className="text-sm text-slate-600">
                          <label htmlFor={`chk-${k}`} className="cursor-pointer">{prefix}</label>
                          <button type="button" onClick={() => abrirDoc(tipo, link)}
                            className="font-semibold text-blue-600 underline underline-offset-2 hover:text-blue-700">
                            {link}
                          </button>
                        </span>
                      </div>
                      <Err msg={errs[k]} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Navegación */}
          <div className="mt-4 flex items-center justify-between">
            {step > 1 ? (
              <button type="button" onClick={prev}
                className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-600 shadow-sm transition hover:bg-slate-50">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>
                Anterior
              </button>
            ) : <div />}

            {step < 3 ? (
              <button type="button" onClick={next}
                className="flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
                style={{ backgroundColor: SIGNAL }}>
                Siguiente
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
              </button>
            ) : (
              <button type="submit" disabled={saving}
                className="flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:opacity-90 disabled:opacity-50"
                style={{ backgroundColor: SIGNAL }}>
                {saving ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeOpacity={.25} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      <path d="M21 12a9 9 0 00-9-9"/>
                    </svg>
                    Enviando…
                  </>
                ) : "Completar registro"}
              </button>
            )}
          </div>
        </form>

        {/* Modal de documento legal */}
        {docModal && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            onClick={() => setDocModal(null)}
          >
            <div
              className="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
                <h3 className="text-sm font-bold" style={{ color: INK }}>{docModal.titulo}</h3>
                <button
                  type="button"
                  onClick={() => setDocModal(null)}
                  className="rounded p-1 text-slate-400 hover:text-slate-600"
                  aria-label="Cerrar"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </div>
              <div className="overflow-y-auto whitespace-pre-wrap px-5 py-4 text-sm leading-relaxed text-slate-600">
                {docLoading ? (
                  <div className="flex items-center gap-2 text-slate-400">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
                    Cargando…
                  </div>
                ) : docError ? (
                  <span className="text-amber-600">{docError}</span>
                ) : (
                  docTexto
                )}
              </div>
              <div className="border-t border-slate-100 px-5 py-3 text-right">
                <button
                  type="button"
                  onClick={() => setDocModal(null)}
                  className="rounded-xl px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                  style={{ backgroundColor: SIGNAL }}
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Scaffold>
  );
}

// ── Layout wrapper ──────────────────────────────────────────────────────────
function Scaffold({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#F1F4F8] px-4 py-10">
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="pb-1 pt-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">
      {children}
    </p>
  );
}
