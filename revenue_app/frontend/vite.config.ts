import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5131,
    proxy: {
      "/api": "http://127.0.0.1:8151",
      "/auth": "http://127.0.0.1:8151",
      "/konto": "http://127.0.0.1:8151",
    },
  },
  build: {
    sourcemap: false,
    target: "es2022",
  },
});
