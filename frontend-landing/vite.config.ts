import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// La landing pública usa el alta self-service del CONTROL PLANE (signup).
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8003";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: { "/api": { target, changeOrigin: true } },
    watch: { usePolling: true, interval: 1000 },
  },
});
