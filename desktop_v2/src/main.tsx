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
import "./styles/app-shell.css";
import "./styles/build.css";
import "./styles/module-content.css";
import "./styles/module-metrics.css";
import "./styles/module-charts.css";
import "./styles/module-filters.css";
import "./styles/responsive.css";
import "./styles/dark-theme.css";

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
