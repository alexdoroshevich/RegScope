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
  // three.js 0.175+ removed pre-built files from the npm package.
  // Excluding these from esbuild pre-bundling lets Vite serve their
  // source files directly at request time instead.
  optimizeDeps: {
    exclude: ["three", "react-force-graph"],
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    alias: {
      // react-force-graph bundles three.js which can't resolve in jsdom.
      // Replace with a lightweight stub that renders a plain div.
      "react-force-graph": new URL(
        "./tests/__mocks__/react-force-graph.tsx",
        import.meta.url,
      ).pathname,
    },
  },
});
