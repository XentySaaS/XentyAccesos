import { Link } from "react-router-dom";

/**
 * Pie con acceso PERMANENTE a los documentos legales (aviso de privacidad / términos).
 * Deben estar disponibles siempre, no solo durante el registro (obligación del responsable).
 * Las rutas `/legal/*` son públicas: funcionan con o sin sesión.
 */
export default function LegalFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white px-4 py-3">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-1.5 text-center text-xs text-slate-400 sm:flex-row sm:text-left">
        <span>Xenty Accesos © {new Date().getFullYear()}</span>
        <nav className="flex items-center gap-4">
          <Link to="/legal/aviso-privacidad" className="transition hover:text-slate-600">
            Aviso de Privacidad
          </Link>
          <Link to="/legal/terminos" className="transition hover:text-slate-600">
            Términos y Condiciones
          </Link>
        </nav>
      </div>
    </footer>
  );
}
