import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { useAuth } from "../store/auth";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "/" });

// Inyecta el access token en cada peticion.
api.interceptors.request.use((config) => {
  const { access } = useAuth.getState();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
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
        logout();
        window.location.href = "/?sesion=expirada";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
