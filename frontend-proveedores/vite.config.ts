import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxy /api -> backend (data plane). En Docker apunta al servicio 'backend'; en local a :8002.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8002";

export default defineConfig({
  // Se sirve en la RAÍZ de dos hosts propios (Nginx): proveedores.<dominio> (hub) y
  // <slug>.proveedores.<dominio> (panel del tenant). El path viejo /proveedores/ redirige 301.
  plugins: [react()],
  server: {
    host: true,
    port: 5175,
    proxy: { "/api": { target, changeOrigin: true } },
    watch: { usePolling: true, interval: 1000 },
  },
});
