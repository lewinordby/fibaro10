import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: {
    port: 5135,
    proxy: {
      "/api": "http://127.0.0.1:8155",
      "/auth": "http://127.0.0.1:8155",
      "/konto": "http://127.0.0.1:8155",
    },
  },
  build: {
    sourcemap: false,
    target: "es2022",
  },
});
