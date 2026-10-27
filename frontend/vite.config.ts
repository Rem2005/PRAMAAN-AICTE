import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The backend port is configuration, not a constant: set
// VITE_API_PROXY_TARGET when the API listens somewhere else. The default is
// the port documented in README.md and backend/README.md.
const DEFAULT_API_TARGET = "http://127.0.0.1:8002";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_PROXY_TARGET?.trim() || DEFAULT_API_TARGET;

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // Same-origin proxy so the session cookie is first-party in development.
      // Cross-site cookies would require SameSite=None plus TLS, which a local
      // prototype does not have.
      proxy: {
        "/api": apiTarget,
        "/health": apiTarget,
      },
    },
    test: {
      environment: "jsdom",
    },
  };
});
