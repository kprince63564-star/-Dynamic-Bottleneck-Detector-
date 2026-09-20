import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies /api requests to the FastAPI backend during local dev so the
// frontend can just call fetch("/api/...") without hardcoding a host/port
// (makes it trivial to demo on a different machine/port without code edits).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
