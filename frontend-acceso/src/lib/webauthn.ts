import { startAuthentication, startRegistration } from "@simplewebauthn/browser";
import api from "../api/client";

// Base del data plane (Usuario del tenant).
const BASE = "/api/auth/mfa/webauthn";

/** Registra una nueva llave/passkey para el usuario autenticado. */
export async function registrarLlave(nombre: string): Promise<void> {
  const { data: optionsJSON } = await api.post(`${BASE}/registro/opciones/`, {});
  const credential = await startRegistration({ optionsJSON });
  await api.post(`${BASE}/registro/verificar/`, { credential, nombre });
}

/** Completa el 2º factor con una llave; devuelve tokens 'full'. */
export async function autenticarLlave(): Promise<{ access: string; refresh: string }> {
  const { data: optionsJSON } = await api.post(`${BASE}/login/opciones/`, {});
  const credential = await startAuthentication({ optionsJSON });
  const { data } = await api.post(`${BASE}/login/verificar/`, { credential });
  return data;
}

export function webauthnDisponible(): boolean {
  return typeof window !== "undefined" && !!window.PublicKeyCredential;
}
