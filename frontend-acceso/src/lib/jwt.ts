/** Decodifica el payload de un JWT SIN verificar la firma (solo lectura de claims en el cliente). */
export function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

/** True si la sesión del token quedó con MFA pendiente (el servidor lo exige antes de dar acceso). */
export function mfaPendiente(access: string): boolean {
  return decodeJwt(access)?.mfa === "pending";
}
