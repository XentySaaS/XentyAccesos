import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  access: string | null;
  refresh: string | null;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

// Contexto de autenticacion: acceso
export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      access: null,
      refresh: null,
      setTokens: (access, refresh) => set({ access, refresh }),
      logout: () => set({ access: null, refresh: null }),
    }),
    { name: "xenty-acceso-auth" }
  )
);
