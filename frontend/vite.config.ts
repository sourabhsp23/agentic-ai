import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, /api is proxied to the FastAPI backend. In Docker, nginx does the same job.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
  build: {
    rollupOptions: {
      output: {
        // Long-cacheable vendor chunks: app deploys don't invalidate library downloads.
        manualChunks: {
          vendor: [
            "react",
            "react-dom",
            "@tanstack/react-query",
            "zustand",
            "@radix-ui/react-select",
            "@radix-ui/react-tooltip",
          ],
          charts: ["chart.js", "react-chartjs-2"],
        },
      },
    },
  },
});
