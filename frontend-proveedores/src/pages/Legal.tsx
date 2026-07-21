import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate, useParams } from "react-router-dom";

// Documento legal público (aviso de privacidad / términos), visible SIN sesión: se puede consultar
// antes, durante y después del registro. Usa un axios plano (sin el interceptor de auth/401 del
// cliente principal) porque el endpoint es AllowAny y la página funciona con o sin token.
const http = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "/" });

// slug de la URL → tipo del backend + título mostrado.
const DOCS: Record<string, { tipo: string; titulo: string }> = {
  "aviso-privacidad": { tipo: "aviso_privacidad", titulo: "Aviso de Privacidad" },
  terminos: { tipo: "terminos_condiciones", titulo: "Términos y Condiciones" },
};

interface Doc {
  texto: string;
  version: number;
  vigente_desde: string | null;
}

type Estado = "cargando" | "ok" | "no-publicado" | "desconocido" | "error";

export default function Legal() {
  const { tipo: slug = "" } = useParams();
  const navigate = useNavigate();
  const meta = DOCS[slug];
  const [doc, setDoc] = useState<Doc | null>(null);
  const [estado, setEstado] = useState<Estado>("cargando");

  useEffect(() => {
    const m = DOCS[slug];
    if (!m) {
      setEstado("desconocido");
      return;
    }
    setEstado("cargando");
    http
      .get<Doc>(`/api/privacidad/documento/${m.tipo}/`)
      .then((r) => {
        setDoc(r.data);
        setEstado("ok");
      })
      .catch((e) => setEstado(e?.response?.status === 404 ? "no-publicado" : "error"));
  }, [slug]);

  const volver = () => {
    // Si se abrió con historial (desde el portal), regresa; si se abrió directo, va al inicio.
    if (window.history.length > 1) navigate(-1);
    else navigate("/");
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#F1F4F8" }}>
      {/* Encabezado */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <img src={`${import.meta.env.BASE_URL}xenty.png`} alt="Xenty" className="h-7 w-auto" />
          <button
            onClick={volver}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Volver
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100 sm:p-8">
          <h1 className="text-xl font-bold" style={{ color: "#0F1B2D" }}>
            {meta?.titulo ?? "Documento legal"}
          </h1>

          {estado === "cargando" && (
            <div className="mt-6 space-y-3">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-4 animate-pulse rounded bg-slate-100" style={{ width: `${90 - i * 5}%` }} />
              ))}
            </div>
          )}

          {estado === "ok" && doc && (
            <>
              <p className="mt-1 text-xs text-slate-400">
                Versión vigente: v{doc.version}
                {doc.vigente_desde
                  ? ` · desde ${new Date(doc.vigente_desde).toLocaleDateString("es-MX")}`
                  : ""}
              </p>
              <div className="mt-5 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {doc.texto}
              </div>
            </>
          )}

          {estado === "no-publicado" && (
            <p className="mt-6 rounded-lg bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
              Este documento aún no ha sido publicado por el responsable. Solicítalo a tu contacto en
              el recinto.
            </p>
          )}

          {estado === "desconocido" && (
            <p className="mt-6 rounded-lg bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
              El documento solicitado no existe.
            </p>
          )}

          {estado === "error" && (
            <p className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-center text-sm text-red-700">
              No se pudo cargar el documento. Intenta de nuevo más tarde.
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
