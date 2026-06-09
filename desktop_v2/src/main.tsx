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
          colorPrimary: "#123766",
          colorSuccess: "#16834a",
          colorWarning: "#bd6b13",
          colorError: "#c24131",
          colorInfo: "#2f5f9b",
          borderRadius: 8,
          fontFamily:
            'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        components: {
          Card: {
            borderRadiusLG: 8,
            paddingLG: 18,
          },
          Layout: {
            bodyBg: "#f4f7f7",
            siderBg: "#f8faf9",
            triggerBg: "#f8faf9",
          },
        },
      }}
    >
      <AntApp>
        <BrowserRouter basename="/v2">
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
