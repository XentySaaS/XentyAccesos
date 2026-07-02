import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { useAuth } from "../store/auth";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "/" });

// Inyecta el access token en cada peticion.
api.interceptors.request.use((config) => {
  const { access } = useAuth.getState();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

/* ── Idempotencia: evita registros duplicados por doble clic ──────────────────
 * 1. Dedupe en vuelo: si ya hay una peticion identica pendiente, se reutiliza su promesa.
 * 2. Header Idempotency-Key: el backend deduplica reintentos (mismo key → repite la
 *    respuesta cacheada en vez de volver a insertar). Estable en reintentos (p. ej. tras 401).
 */
const UNSAFE = new Set(["post", "put", "patch"]);
const enVuelo = new Map<string, Promise<AxiosResponse>>();

function nuevoKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `k-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

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

// En 401, intenta refrescar una sola vez (rotacion + blacklist en el backend) y reintenta.
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
            .finally(() => {
              refreshing = null;
            });
        }
        const access = await refreshing;
        if (access) {
          original.headers.Authorization = `Bearer ${access}`;
          return api(original);
        }
      } catch {
        useAuth.getState().logout();
      }
    }
    return Promise.reject(error);
  }
);

export default api;
