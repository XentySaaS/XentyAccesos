import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { useAuth } from "../store/auth";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "/" });

// Inyecta el access token en cada petición.
api.interceptors.request.use((config) => {
  const { access } = useAuth.getState();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

/* ── Idempotencia: evita registros duplicados por doble clic ──────────────────
 * Cuando el usuario da clic y la petición aún no responde ("no reacciona"),
 * un segundo clic dispararía un segundo POST y crearía un registro duplicado.
 * Dos capas de defensa, transparentes para todos los formularios (actuales y futuros):
 *   1. Dedupe en vuelo: si ya hay una petición idéntica pendiente, se reutiliza su
 *      promesa en vez de mandar otra.
 *   2. Header Idempotency-Key: el backend deduplica reintentos de red (mismo key →
 *      repite la respuesta cacheada en vez de volver a insertar). El key es estable
 *      para una misma operación (se conserva en reintentos, p. ej. tras refrescar token).
 */
const UNSAFE = new Set(["post", "put", "patch"]);
const enVuelo = new Map<string, Promise<AxiosResponse>>();

function nuevoKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `k-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// Firma de la operación para el dedupe en vuelo. FormData (archivos) no es serializable:
// se le da una firma única por llamada para que nunca se deduplique por error.
function firma(method: string, url: string, data: unknown): string {
  if (typeof FormData !== "undefined" && data instanceof FormData) {
    return `${method}:${url}:formdata:${nuevoKey()}`;
  }
  let cuerpo = "";
  try { cuerpo = data == null ? "" : JSON.stringify(data); } catch { cuerpo = nuevoKey(); }
  return `${method}:${url}:${cuerpo}`;
}

api.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (UNSAFE.has(method) && !config.headers["Idempotency-Key"]) {
    config.headers["Idempotency-Key"] = nuevoKey();
  }
  return config;
});

// Envuelve los métodos mutadores para deduplicar peticiones idénticas en vuelo.
(["post", "put", "patch"] as const).forEach((m) => {
  const original = api[m].bind(api) as (url: string, data?: unknown, config?: object) => Promise<AxiosResponse>;
  // @ts-expect-error — se conserva la firma de uso (api.post<T>(url, body, config)).
  api[m] = (url: string, data?: unknown, config?: object) => {
    const key = firma(m, url, data);
    const pendiente = enVuelo.get(key);
    if (pendiente) return pendiente;
    const p = original(url, data, config).finally(() => enVuelo.delete(key));
    enVuelo.set(key, p);
    return p;
  };
});

// En 401: intenta refrescar una sola vez (rotación + blacklist); si falla → login con aviso.
let refreshing: Promise<string | null> | null = null;

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      const { refresh, setTokens, logout } = useAuth.getState();
      if (!refresh) {
        logout();
        window.location.href = "/?sesion=expirada";
        return Promise.reject(error);
      }
      try {
        if (!refreshing) {
          refreshing = axios
            .post(`${api.defaults.baseURL}api/auth/refresh/`, { refresh })
            .then((res) => {
              setTokens(res.data.access, res.data.refresh ?? refresh);
              return res.data.access as string;
            })
            .finally(() => { refreshing = null; });
        }
        const access = await refreshing;
        if (access) {
          // Reintenta con el MISMO Idempotency-Key (original.headers ya lo trae): si el POST
          // llegó a ejecutarse antes del 401, el backend repite la respuesta sin duplicar.
          original.headers.Authorization = `Bearer ${access}`;
          return api(original);
        }
      } catch {
        logout();
        window.location.href = "/?sesion=expirada";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
