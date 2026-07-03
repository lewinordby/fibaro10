import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/",
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalized = id.replaceAll("\\", "/");
          if (!normalized.includes("/node_modules/")) return undefined;
          if (normalized.includes("/antd/") || normalized.includes("/@ant-design/icons/") || normalized.includes("/rc-")) {
            return "antd-core";
          }
          if (normalized.includes("/react/") || normalized.includes("/react-dom/")) {
            return "react";
          }
          return undefined;
        },
      },
    },
  },
});
