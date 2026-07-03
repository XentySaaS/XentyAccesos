/** Decodifica el payload de un JWT en el cliente (solo lectura de claims; sin verificar firma). */
export interface JwtClaims {
  mfa?: string;   // "pending" (sesión MFA incompleta) | "ok"
  ctx?: string;
  exp?: number;
  [k: string]: unknown;
}

export function decodeJwt(token: string): JwtClaims | null {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as JwtClaims;
  } catch {
    return null;
  }
}

/** true si el access token corresponde a una sesión con MFA aún por verificar. */
export function mfaPendiente(access: string): boolean {
  return decodeJwt(access)?.mfa === "pending";
}
