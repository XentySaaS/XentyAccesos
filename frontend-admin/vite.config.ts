import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// La SPA admin habla con el CONTROL PLANE. En Docker apunta a 'superadmin-backend'; en local a :8003.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8003";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5176,
    proxy: { "/api": { target, changeOrigin: true } },
    watch: { usePolling: true, interval: 1000 },
  },
});
