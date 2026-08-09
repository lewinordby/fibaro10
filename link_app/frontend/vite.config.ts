import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/koble/",
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: {
    port: 5138,
    proxy: {
      "/api": "http://127.0.0.1:8158",
      "/auth": "http://127.0.0.1:8158",
      "/konto": "http://127.0.0.1:8158",
    },
  },
  build: { sourcemap: false, target: "es2022" },
});
