import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxy /api -> backend (data plane). En Docker apunta al servicio 'backend'; en local a :8002.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8002";

export default defineConfig({
  base: "/proveedores/",  // se sirve bajo <tenant>.localhost/proveedores/ (Nginx)
  plugins: [react()],
  server: {
    host: true,
    port: 5175,
    proxy: { "/api": { target, changeOrigin: true } },
  },
});
