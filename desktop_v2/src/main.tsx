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
          colorPrimary: "#326fa8",
          colorSuccess: "#4fa35a",
          colorWarning: "#d29713",
          colorError: "#b84f45",
          colorInfo: "#326fa8",
          colorText: "#182436",
          colorTextSecondary: "#6b778c",
          colorBorder: "#dfe6ee",
          colorBgLayout: "#f3f6fa",
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
            bodyBg: "#f3f6fa",
            siderBg: "#071a45",
            triggerBg: "#071a45",
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
