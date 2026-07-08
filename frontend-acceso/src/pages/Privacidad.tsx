import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";
import { Ayuda } from "../components/Ayuda";

interface Titular {
  titular_tipo: "empleado" | "cuenta_proveedor" | "asistente";
  titular_id: number;
  nombre: string;
  email: string | null;
  estado: string | null;
}
interface Solicitud {
  id: number;
  tipo: string;
  titular_tipo: string;
  titular_id: number;
  titular_desc: string;
  estado: string;
  motivo: string | null;
  plazo_limite: string;
  resuelto: string | null;
  creado: string;
}

const INK = "#0F1B2D";
const SIGNAL = "#2563EB";
const inputCls =
  "w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

const TIPO_TITULAR: Record<string, string> = {
  empleado: "Empleado",
  cuenta_proveedor: "Cuenta de proveedor",
  asistente: "Asistente de cita",
};
const TIPO_SOLICITUD: Record<string, string> = {
  acceso: "Acceso",
  rectificacion: "Rectificación",
  cancelacion: "Cancelación",
  oposicion: "Oposición",
};
const ESTADO_SOLICITUD = ["recibida", "en_proceso", "completada", "rechazada"];

export default function Privacidad() {
  const [q, setQ] = useState("");
  const [resultados, setResultados] = useState<Titular[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [solicitudes, setSolicitudes] = useState<Solicitud[]>([]);
  const [docTipo, setDocTipo] = useState<string>("aviso_privacidad");
  const [docVersion, setDocVersion] = useState(0);
  const [docTexto, setDocTexto] = useState("");
  const [cancelTarget, setCancelTarget] = useState<Titular | null>(null);
  const [confirmTxt, setConfirmTxt] = useState("");
  const [msg, setMsg] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [cargando, setCargando] = useState<string | null>(null);

  async function cargarSolicitudes() {
    const { data } = await api.get<{ results?: Solicitud[] } | Solicitud[]>(
      "/api/cumplimiento/arco/solicitudes/",
    );
    setSolicitudes(Array.isArray(data) ? data : (data.results ?? []));
  }
  async function cargarDoc(tipo: string) {
    const { data } = await api.get<{ texto: string; version: number }>(
      `/api/cumplimiento/arco/documentos/${tipo}/`,
    );
    setDocVersion(data.version || 0);
    setDocTexto(data.texto || "");
  }
  useEffect(() => {
    cargarSolicitudes().catch(() => {});
  }, []);
  useEffect(() => {
    cargarDoc(docTipo).catch(() => {});
  }, [docTipo]);

  async function buscar(e: FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setBuscando(true);
    setMsg(null);
    try {
      const { data } = await api.get<{ resultados: Titular[] }>(
        `/api/cumplimiento/arco/titulares/?q=${encodeURIComponent(q.trim())}`,
      );
      setResultados(data.resultados);
    } finally {
      setBuscando(false);
    }
  }

  async function exportar(t: Titular) {
    setMsg(null);
    setCargando(`export-${t.titular_tipo}-${t.titular_id}`);
    try {
      const res = await api.get(`/api/cumplimiento/arco/export/${t.titular_tipo}/${t.titular_id}/`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `arco_${t.titular_tipo}_${t.titular_id}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setMsg({ tipo: "ok", texto: "Datos del titular exportados (JSON descargado)." });
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo exportar." });
    } finally {
      setCargando(null);
    }
  }

  async function confirmarCancelacion(e: FormEvent) {
    e.preventDefault();
    if (!cancelTarget || confirmTxt !== "ANONIMIZAR") return;
    setCargando("cancelar");
    setMsg(null);
    try {
      await api.post(
        `/api/cumplimiento/arco/cancelar/${cancelTarget.titular_tipo}/${cancelTarget.titular_id}/`,
        {},
      );
      setMsg({ tipo: "ok", texto: "Titular anonimizado. Se registró la solicitud de cancelación." });
      setCancelTarget(null);
      setConfirmTxt("");
      // Refresca la lista de resultados y las solicitudes.
      if (q.trim().length >= 2) await buscar({ preventDefault() {} } as FormEvent);
      await cargarSolicitudes();
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo anonimizar al titular." });
    } finally {
      setCargando(null);
    }
  }

  async function cambiarEstado(s: Solicitud, estado: string) {
    try {
      await api.patch(`/api/cumplimiento/arco/solicitudes/${s.id}/`, { estado });
      await cargarSolicitudes();
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo actualizar la solicitud." });
    }
  }

  async function guardarDoc(e: FormEvent) {
    e.preventDefault();
    if (!docTexto.trim()) return;
    setCargando("doc");
    setMsg(null);
    try {
      const { data } = await api.put<{ texto: string; version: number }>(
        `/api/cumplimiento/arco/documentos/${docTipo}/`,
        { texto: docTexto },
      );
      setDocVersion(data.version);
      setMsg({ tipo: "ok", texto: `Documento publicado (v${data.version}).` });
    } catch {
      setMsg({ tipo: "error", texto: "No se pudo publicar el documento." });
    } finally {
      setCargando(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: INK }}>
          Privacidad · Derechos ARCO
        </h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Atención de derechos ARCO (LFPDPPP): acceso a los datos de un titular, cancelación
          (anonimización) y gestión del aviso de privacidad.
        </p>
      </div>

      {msg && (
        <div
          className={`mb-4 rounded-lg px-4 py-2.5 text-sm ring-1 ${
            msg.tipo === "ok"
              ? "bg-green-50 text-green-700 ring-green-100"
              : "bg-red-50 text-red-700 ring-red-100"
          }`}
        >
          {msg.texto}
        </div>
      )}

      {/* Titulares */}
      <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
        <h2 className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-slate-700">
          Titular de datos
          <Ayuda>
            Busca por nombre o correo a la persona que ejerce su derecho. Puedes exportar todos sus
            datos personales (derecho de acceso) o anonimizarlos (cancelación).
          </Ayuda>
        </h2>
        <form onSubmit={buscar} className="mt-2 flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Nombre o correo del titular…"
            className={inputCls}
          />
          <button
            type="submit"
            disabled={buscando || q.trim().length < 2}
            className="whitespace-nowrap rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            style={{ backgroundColor: SIGNAL }}
          >
            {buscando ? "Buscando…" : "Buscar"}
          </button>
        </form>

        {resultados.length > 0 && (
          <ul className="mt-3 divide-y divide-slate-50">
            {resultados.map((t) => (
              <li
                key={`${t.titular_tipo}-${t.titular_id}`}
                className="flex items-center gap-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium" style={{ color: INK }}>
                    {t.nombre}
                  </p>
                  <p className="truncate text-xs text-slate-400">
                    {TIPO_TITULAR[t.titular_tipo]} · {t.email || "sin correo"}
                    {t.estado ? ` · ${t.estado}` : ""}
                  </p>
                </div>
                <button
                  onClick={() => exportar(t)}
                  disabled={cargando === `export-${t.titular_tipo}-${t.titular_id}`}
                  className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                >
                  Exportar datos
                </button>
                <button
                  onClick={() => {
                    setCancelTarget(t);
                    setConfirmTxt("");
                  }}
                  className="rounded-lg border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                >
                  Anonimizar
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Solicitudes */}
      <div className="mt-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
        <h2 className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-slate-700">
          Solicitudes ARCO
          <Ayuda>
            Registro de solicitudes y su plazo legal de respuesta (20 días naturales, LFPDPPP art.
            32). Cambia el estado conforme las atiendes.
          </Ayuda>
        </h2>
        {solicitudes.length === 0 ? (
          <p className="mt-2 rounded-lg bg-slate-50 px-3 py-4 text-center text-xs text-slate-400">
            Sin solicitudes registradas.
          </p>
        ) : (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-2 py-2">Tipo</th>
                  <th className="px-2 py-2">Titular</th>
                  <th className="px-2 py-2">Plazo</th>
                  <th className="px-2 py-2">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {solicitudes.map((s) => (
                  <tr key={s.id}>
                    <td className="px-2 py-2">{TIPO_SOLICITUD[s.tipo] ?? s.tipo}</td>
                    <td className="px-2 py-2 text-slate-500">
                      {TIPO_TITULAR[s.titular_tipo]} · {s.titular_desc}
                    </td>
                    <td className="px-2 py-2 text-slate-500">{s.plazo_limite}</td>
                    <td className="px-2 py-2">
                      <select
                        value={s.estado}
                        onChange={(e) => cambiarEstado(s, e.target.value)}
                        className="rounded-lg border border-slate-200 px-2 py-1 text-xs outline-none focus:border-blue-500"
                      >
                        {ESTADO_SOLICITUD.map((es) => (
                          <option key={es} value={es}>
                            {es}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Documentos legales (aviso de privacidad + términos y condiciones) */}
      <form
        onSubmit={guardarDoc}
        className="mt-4 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-100"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            Documentos legales
            <Ayuda>
              Textos que el proveedor lee y acepta al registrarse. Cada vez que guardas se crea una
              versión nueva (histórico), para poder probar cuál estaba vigente.
            </Ayuda>
          </h2>
          {docVersion > 0 && (
            <span className="text-xs text-slate-400">Versión vigente: v{docVersion}</span>
          )}
        </div>
        {/* Selector de documento */}
        <div className="mt-3 flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          {[
            { k: "aviso_privacidad", label: "Aviso de Privacidad" },
            { k: "terminos_condiciones", label: "Términos y Condiciones" },
          ].map((d) => (
            <button
              key={d.k}
              type="button"
              onClick={() => setDocTipo(d.k)}
              className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition ${
                docTipo === d.k
                  ? "bg-white text-blue-600 shadow-sm ring-1 ring-slate-200"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
        <textarea
          value={docTexto}
          onChange={(e) => setDocTexto(e.target.value)}
          rows={10}
          placeholder="Redacta aquí el texto del documento…"
          className={`${inputCls} mt-3 resize-y`}
        />
        <button
          type="submit"
          disabled={cargando === "doc" || !docTexto.trim()}
          className="mt-3 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: SIGNAL }}
        >
          {cargando === "doc" ? "Publicando…" : "Publicar nueva versión"}
        </button>
      </form>

      {/* Modal de confirmación de anonimización */}
      {cancelTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <form
            onSubmit={confirmarCancelacion}
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
          >
            <h2 className="text-base font-bold text-red-700">Anonimizar titular</h2>
            <p className="mt-2 text-sm text-slate-600">
              Vas a borrar de forma <strong>irreversible</strong> los datos personales de{" "}
              <strong>{cancelTarget.nombre}</strong> ({TIPO_TITULAR[cancelTarget.titular_tipo]}):
              nombre, contacto, identificaciones y archivos (INE, fotos, documentos). El registro se
              conserva anonimizado para la bitácora.
            </p>
            <label className="mt-4 block text-sm">
              <span className="mb-1 block font-medium text-slate-700">
                Escribe <code className="rounded bg-slate-100 px-1">ANONIMIZAR</code> para confirmar
              </span>
              <input
                value={confirmTxt}
                onChange={(e) => setConfirmTxt(e.target.value)}
                className={inputCls}
                autoFocus
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setCancelTarget(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={confirmTxt !== "ANONIMIZAR" || cargando === "cancelar"}
                className="rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
              >
                {cargando === "cancelar" ? "Anonimizando…" : "Anonimizar"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
