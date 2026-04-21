import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

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
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    alias: {
      // react-force-graph-2d draws to <canvas> which jsdom does not implement.
      // Replace with a lightweight stub that renders a plain div.
      "react-force-graph-2d": new URL(
        "./tests/__mocks__/react-force-graph-2d.tsx",
        import.meta.url,
      ).pathname,
    },
  },
});
