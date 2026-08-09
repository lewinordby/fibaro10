import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/energi/",
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: {
    port: 5134,
    proxy: {
      "/api": "http://127.0.0.1:8154",
      "/auth": "http://127.0.0.1:8154",
      "/konto": "http://127.0.0.1:8154",
    },
  },
  build: {
    sourcemap: false,
    target: "es2022",
  },
});
