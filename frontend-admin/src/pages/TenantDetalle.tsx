import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client";

interface Tenant {
  id: number;
  schema_name: string;
  nombre: string;
  estado: string;
  trial_ends_at: string | null;
  modo_solo_lectura: boolean;
  plan: string | null;
  saldo: number;
}

interface Checkout {
  sandbox: boolean;
  tipo: string;
  checkout_url: string;
  id?: string;
}

const INK = "#0F1B2D";

const ESTADO_BADGE: Record<string, { bg: string; text: string; label: string; dot: string }> = {
  trial:      { bg: "bg-blue-100",  text: "text-blue-700",  label: "Trial",      dot: "#2563EB" },
  activo:     { bg: "bg-green-100", text: "text-green-800", label: "Activo",     dot: "#16A34A" },
  suspendido: { bg: "bg-amber-100", text: "text-amber-700", label: "Suspendido", dot: "#D97706" },
  cancelado:  { bg: "bg-red-100",   text: "text-red-700",   label: "Cancelado",  dot: "#DC2626" },
};

function fecha(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}

export default function TenantDetalle() {
  const { id } = useParams<{ id: string }>();
  const [t, setT]           = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null); // acción en curso
  const [checkout, setCheckout] = useState<Checkout | null>(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Tenant>(`/api/admin/tenants/${id}/`);
      setT(data);
    } catch {
      setError("No se pudo cargar el tenant.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { cargar(); }, [cargar]);

  async function accion(nombre: "suspender" | "activar" | "cancelar") {
    setOcupado(nombre);
    setError(null);
    try {
      const { data } = await api.post<Tenant>(`/api/admin/tenants/${id}/${nombre}/`);
      setT(data);
    } catch {
      setError(`No se pudo ${nombre} el tenant.`);
    } finally {
      setOcupado(null);
    }
  }

  async function generarCheckout() {
    setOcupado("checkout");
    setError(null);
    setCheckout(null);
    try {
      const { data } = await api.post<Checkout>(`/api/admin/tenants/${id}/checkout/`);
      setCheckout(data);
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail ?? "No se pudo generar el checkout.");
    } finally {
      setOcupado(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!t) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-slate-500">{error ?? "Tenant no encontrado."}</p>
        <Link to="/tenants" className="mt-3 inline-block text-sm font-medium text-blue-600 hover:underline">
          ← Volver a Tenants
        </Link>
      </div>
    );
  }

  const b = ESTADO_BADGE[t.estado] ?? { bg: "bg-slate-100", text: "text-slate-700", label: t.estado, dot: "#64748B" };

  return (
    <div className="mx-auto max-w-4xl">
      {/* Migas + encabezado */}
      <Link to="/tenants" className="text-sm font-medium text-slate-400 hover:text-slate-600">
        ← Tenants
      </Link>
      <div className="mt-2 mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold" style={{ color: INK }}>{t.nombre}</h1>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${b.bg} ${b.text}`}>
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: b.dot }} />
          {b.label}
        </span>
        {t.modo_solo_lectura && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
            solo lectura
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700 ring-1 ring-red-100">
          {error}
        </div>
      )}

      {/* Datos de la suscripción */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Dato label="Subdominio" valor={t.schema_name} mono />
        <Dato label="Plan" valor={t.plan ?? "Sin plan"} />
        <Dato label="Créditos" valor={String(t.saldo)} />
        <Dato label="Fin de trial" valor={fecha(t.trial_ends_at)} />
      </div>

      {/* Acciones de ciclo de vida */}
      <div className="mt-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
        <h2 className="text-sm font-semibold text-slate-700">Ciclo de vida</h2>
        <p className="mt-0.5 text-xs text-slate-400">
          El estado gobierna los middlewares de enforcement (acceso del cliente al SaaS).
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {t.estado !== "activo" && (
            <button
              onClick={() => accion("activar")}
              disabled={ocupado !== null}
              className="rounded-lg bg-[#16A34A] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {ocupado === "activar" ? "Activando…" : "Activar"}
            </button>
          )}
          {t.estado !== "suspendido" && t.estado !== "cancelado" && (
            <button
              onClick={() => accion("suspender")}
              disabled={ocupado !== null}
              className="rounded-lg border border-slate-200 px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              {ocupado === "suspender" ? "Suspendiendo…" : "Suspender"}
            </button>
          )}
          {t.estado !== "cancelado" && (
            <button
              onClick={() => accion("cancelar")}
              disabled={ocupado !== null}
              className="rounded-lg border border-red-200 px-3.5 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              {ocupado === "cancelar" ? "Cancelando…" : "Cancelar suscripción"}
            </button>
          )}
        </div>
      </div>

      {/* Billing / Stripe */}
      <div className="mt-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
        <h2 className="text-sm font-semibold text-slate-700">Billing</h2>
        <p className="mt-0.5 text-xs text-slate-400">
          Genera una sesión de checkout de suscripción de Stripe para este tenant.
        </p>
        <div className="mt-4">
          <button
            onClick={generarCheckout}
            disabled={ocupado !== null}
            className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {ocupado === "checkout" ? "Generando…" : "Generar checkout de suscripción"}
          </button>
        </div>
        {checkout && (
          <div className="mt-4 rounded-lg bg-slate-50 px-4 py-3 ring-1 ring-slate-100">
            {checkout.sandbox && (
              <span className="mb-1.5 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                modo sandbox
              </span>
            )}
            <p className="text-xs text-slate-500">URL de checkout</p>
            <a
              href={checkout.checkout_url}
              target="_blank"
              rel="noreferrer"
              className="mt-0.5 block break-all text-sm font-medium text-blue-600 hover:underline"
            >
              {checkout.checkout_url}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

function Dato({ label, valor, mono }: { label: string; valor: string; mono?: boolean }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <p className={`mt-1 text-lg font-semibold text-slate-800 ${mono ? "font-mono text-base" : ""}`}>{valor}</p>
    </div>
  );
}
