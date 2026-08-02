import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: {
    port: 5132,
    proxy: {
      "/api": "http://127.0.0.1:8152",
      "/auth": "http://127.0.0.1:8152",
      "/konto": "http://127.0.0.1:8152",
    },
  },
  build: {
    sourcemap: false,
    target: "es2022",
  },
});
