import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/",
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replaceAll("\\", "/");
          if (!normalizedId.includes("/node_modules/")) return undefined;
          if (normalizedId.includes("/echarts/") || normalizedId.includes("/zrender/") || normalizedId.includes("/echarts-for-react/")) {
            return "charts";
          }
          if (
            normalizedId.includes("/antd/") ||
            normalizedId.includes("/@ant-design/icons/") ||
            normalizedId.includes("/rc-") ||
            normalizedId.includes("/@rc-component/")
          ) {
            return "antd-core";
          }
          if (
            normalizedId.includes("/react/") ||
            normalizedId.includes("/react-dom/") ||
            normalizedId.includes("/react-router-dom/")
          ) {
            return "react";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8110",
    },
  },
});
