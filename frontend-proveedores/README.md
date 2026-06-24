# Xenty Proveedores

SPA del contexto **proveedores** de Xenty Acceso (Vite + React + TS + Tailwind + Zustand + Axios).

```bash
npm install
npm run dev      # http://localhost:5175  (proxy /api -> backend :8002)
```

- `src/api/client.ts` — Axios con inyeccion de JWT e intento de refresh en 401.
- `src/store/auth.ts` — estado de sesion (Zustand, persistido).
- Login -> `/api/auth/proveedores/login/`; pantalla protegida `/dashboard` consulta `/api/auth/me/`.
- shadcn/ui se anade por componente en fases posteriores.
