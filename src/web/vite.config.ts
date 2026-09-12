import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em dev, /api vai para a API local; em produção o Caddy faz o mesmo (mesma origem, sem CORS).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: process.env.API_URL ?? "http://localhost:8000", changeOrigin: false } },
  },
  build: { outDir: "dist", sourcemap: false },
});
