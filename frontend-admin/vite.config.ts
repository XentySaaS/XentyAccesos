import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// La SPA admin habla con el CONTROL PLANE (superadmin-backend, puerto 8003).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5176,
    proxy: { "/api": { target: "http://localhost:8003", changeOrigin: true } },
  },
});
