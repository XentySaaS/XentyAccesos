import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../store/auth";

const INK = "#0F1B2D";

interface Info {
  tenant: {
    nombre: string;
    estado: string;
    estado_label: string;
    trial_ends_at: string | null;
    gracia_hasta: string | null;
  };
  plan: { nombre: string; descripcion: string | null; precio_mensual: string; modulos: string[] } | null;
  suscripcion: {
    estado: string;
    estado_label: string;
    periodo_fin: string | null;
    cancelar_al_fin_periodo: boolean;
  } | null;
}

const ESTADO_BADGE: Record<string, { bg: string; text: string }> = {
  trial:      { bg: "bg-blue-100",  text: "text-blue-800"  },
  activo:     { bg: "bg-green-100", text: "text-green-800" },
  activa:     { bg: "bg-green-100", text: "text-green-800" },
  suspendido: { bg: "bg-amber-100", text: "text-amber-800" },
  morosa:     { bg: "bg-amber-100", text: "text-amber-800" },
  cancelado:  { bg: "bg-red-100",   text: "text-red-700"   },
  cancelada:  { bg: "bg-red-100",   text: "text-red-700"   },
};

function Badge({ estado, label }: { estado: string; label: string }) {
  const c = ESTADO_BADGE[estado] ?? { bg: "bg-slate-100", text: "text-slate-600" };
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${c.bg} ${c.text}`}>{label}</span>;
}

function fmtFecha(s: string | null) {
  return s ? new Date(s).toLocaleDateString("es-MX", { year: "numeric", month: "long", day: "numeric" }) : "—";
}

export default function Suscripcion() {
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();
  const [info, setInfo] = useState<Info | null>(null);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [confirmTxt, setConfirmTxt] = useState("");
  const [cancelando, setCancelando] = useState(false);
  const [error, setError] = useState("");
  const [cancelada, setCancelada] = useState(false);

  useEffect(() => {
    api.get<Info>("/api/suscripcion/")
      .then((r) => setInfo(r.data))
      .catch(() => setError("No se pudo cargar la suscripción."))
      .finally(() => setLoading(false));
  }, []);

  const nombre = info?.tenant.nombre ?? "";

  async function cancelar(e: React.FormEvent) {
    e.preventDefault();
    setCancelando(true); setError("");
    try {
      await api.post("/api/suscripcion/", { confirmacion: confirmTxt });
      setModal(false);
      setCancelada(true); // pantalla terminal: la cuenta quedó cancelada (el tenant ya está bloqueado)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "No se pudo cancelar la cuenta.");
    } finally {
      setCancelando(false);
    }
  }

  function salir() {
    logout();
    navigate("/");
  }

  if (loading) {
    return <div className="py-16 text-center"><div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" /></div>;
  }

  if (cancelada) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-50">
          <svg className="h-7 w-7 text-red-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <h1 className="text-xl font-bold" style={{ color: INK }}>Cuenta cancelada</h1>
        <p className="mt-2 text-sm text-slate-500">
          Tu cuenta quedó cancelada y el acceso está bloqueado. Los datos se conservan; si fue un error,
          contacta a tu proveedor para reactivarla.
        </p>
        <button onClick={salir} className="mt-6 rounded-lg bg-slate-800 px-5 py-2 text-sm font-semibold text-white hover:opacity-90">
          Cerrar sesión
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>Suscripción</h1>
        <p className="mt-0.5 text-sm text-slate-500">Tu plan, estado de la cuenta y opciones de baja.</p>
      </div>

      {error && !modal && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
      )}

      {/* Plan y estado */}
      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Plan actual</p>
            <p className="mt-1 text-lg font-bold" style={{ color: INK }}>{info?.plan?.nombre ?? "Sin plan asignado"}</p>
            {info?.plan?.descripcion && <p className="mt-0.5 text-sm text-slate-500">{info.plan.descripcion}</p>}
          </div>
          {info && <Badge estado={info.tenant.estado} label={info.tenant.estado_label} />}
        </div>

        <dl className="mt-5 grid grid-cols-1 gap-4 border-t border-slate-100 pt-5 sm:grid-cols-2">
          {info?.plan && (
            <div>
              <dt className="text-xs text-slate-400">Precio mensual</dt>
              <dd className="text-sm font-medium text-slate-700">${info.plan.precio_mensual} MXN</dd>
            </div>
          )}
          {info?.suscripcion && (
            <div>
              <dt className="text-xs text-slate-400">Suscripción</dt>
              <dd className="text-sm font-medium text-slate-700">{info.suscripcion.estado_label}</dd>
            </div>
          )}
          {info?.tenant.trial_ends_at && (
            <div>
              <dt className="text-xs text-slate-400">Fin del periodo de prueba</dt>
              <dd className="text-sm font-medium text-slate-700">{fmtFecha(info.tenant.trial_ends_at)}</dd>
            </div>
          )}
          {info?.suscripcion?.periodo_fin && (
            <div>
              <dt className="text-xs text-slate-400">Fin del periodo actual</dt>
              <dd className="text-sm font-medium text-slate-700">{fmtFecha(info.suscripcion.periodo_fin)}</dd>
            </div>
          )}
          {info?.tenant.gracia_hasta && (
            <div>
              <dt className="text-xs text-slate-400">Acceso de gracia hasta</dt>
              <dd className="text-sm font-medium text-slate-700">{fmtFecha(info.tenant.gracia_hasta)}</dd>
            </div>
          )}
        </dl>
        <p className="mt-5 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
          El plan y la facturación los gestiona tu proveedor. Para cambiar de plan, contáctalo.
        </p>
      </div>

      {/* Zona peligrosa */}
      <div className="mt-6 rounded-2xl border border-red-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-bold text-red-700">Zona peligrosa</h2>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="max-w-md">
            <p className="text-sm font-medium text-slate-700">Cancelar cuenta</p>
            <p className="mt-0.5 text-xs text-slate-500">
              Cancela la suscripción y bloquea el acceso de todos los usuarios de esta cuenta. Tus datos
              se conservan; podrás pedir la reactivación a tu proveedor. Esta acción no se hace sola.
            </p>
          </div>
          <button
            onClick={() => { setConfirmTxt(""); setError(""); setModal(true); }}
            className="shrink-0 rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50"
          >
            Cancelar cuenta
          </button>
        </div>
      </div>

      {/* Modal de confirmación */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form onSubmit={cancelar} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="text-base font-bold text-red-700">Cancelar la cuenta</h2>
            <p className="mt-2 text-sm text-slate-600">
              Vas a <strong>cancelar</strong> la cuenta <strong>{nombre}</strong>. Se bloqueará el acceso
              de todos sus usuarios. Para confirmar, escribe el nombre exacto de la cuenta:
            </p>
            <p className="mt-2 rounded bg-slate-100 px-2 py-1 text-center text-sm font-mono">{nombre}</p>
            <input
              value={confirmTxt}
              onChange={(e) => setConfirmTxt(e.target.value)}
              placeholder="Escribe el nombre de la cuenta"
              autoFocus
              className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-400 focus:ring-2 focus:ring-red-100"
            />
            {error && <p className="mt-2 text-xs font-medium text-red-600">{error}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setModal(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Volver
              </button>
              <button
                type="submit"
                disabled={cancelando || confirmTxt.trim().toLowerCase() !== nombre.trim().toLowerCase()}
                className="rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
              >
                {cancelando ? "Cancelando…" : "Sí, cancelar cuenta"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
