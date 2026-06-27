import React from "react";
import ReactDOM from "react-dom/client";
import { App as AntApp, ConfigProvider } from "antd";
import nbNO from "antd/locale/nb_NO";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { antdTheme } from "./designTokens";
import { queryClient } from "./queryClient";
import "./styles/tokens.css";
import "./styles/layout.css";
import "./styles/build.css";
import "./styles/module-content.css";
import "./styles/sun-sessions.css";
import "./styles/status.css";
import "./styles/status-overview.css";
import "./styles/status-comparison.css";
import "./styles/sun-timeline.css";
import "./styles/parking-timeline.css";
import "./styles/ventilation.css";
import "./styles/energy.css";
import "./styles/records.css";
import "./styles/records-settlements.css";
import "./styles/mobile-preview.css";
import "./styles/responsive.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={nbNO}
        theme={antdTheme}
      >
        <AntApp>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
