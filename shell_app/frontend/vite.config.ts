import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5150,
    proxy: {
      "/api": "http://127.0.0.1:8150",
      "/auth": "http://127.0.0.1:8150",
      "/konto": "http://127.0.0.1:8150"
    }
  },
  build: { sourcemap: false, target: "es2022" }
});
