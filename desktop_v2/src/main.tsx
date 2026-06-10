import React from "react";
import ReactDOM from "react-dom/client";
import { App as AntApp, ConfigProvider } from "antd";
import nbNO from "antd/locale/nb_NO";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={nbNO}
      theme={{
        token: {
          colorPrimary: "#2563eb",
          colorSuccess: "#15803d",
          colorWarning: "#f59e0b",
          colorError: "#b91c1c",
          colorInfo: "#2563eb",
          borderRadius: 6,
          fontFamily:
            'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        components: {
          Card: {
            borderRadiusLG: 6,
            paddingLG: 18,
          },
          Layout: {
            bodyBg: "#f8fafc",
            siderBg: "#1f2937",
            triggerBg: "#1f2937",
          },
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
