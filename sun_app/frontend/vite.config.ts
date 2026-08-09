import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/soling/",
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: {
    port: 5133,
    proxy: {
      "/api": "http://127.0.0.1:8153",
      "/auth": "http://127.0.0.1:8153",
      "/konto": "http://127.0.0.1:8153",
    },
  },
  build: {
    sourcemap: false,
    target: "es2022",
  },
});
