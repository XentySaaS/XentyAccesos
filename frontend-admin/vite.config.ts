import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El proxy /api -> backend evita CORS en dev. En prod sirve Nginx.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5176,
    proxy: { "/api": { target: "http://localhost:8002", changeOrigin: true } },
  },
});
