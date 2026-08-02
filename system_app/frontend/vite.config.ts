import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: {
    port: 5137,
    proxy: {
      "/api": "http://127.0.0.1:8157",
      "/auth": "http://127.0.0.1:8157",
      "/konto": "http://127.0.0.1:8157",
    },
  },
  build: {
    sourcemap: false,
    target: "es2022",
  },
});
