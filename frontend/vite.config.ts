import path from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    // lets one ngrok tunnel serve both the app and the API: the app calls /api/..., Vite forwards it to the backend
    proxy: {
      "/api": { target: process.env.API_TARGET ?? "http://localhost:8000", rewrite: (p) => p.replace(/^\/api/, "") },
    },
    allowedHosts: [".ngrok-free.app", ".ngrok-free.dev", ".ngrok.app", ".ngrok.dev", ".ngrok.io"],
  },
  test: {
    // jsdom, not node: importing page modules pulls in leaflet, which
    // touches `document` at import time for browser feature detection
    environment: "jsdom",
  },
});
