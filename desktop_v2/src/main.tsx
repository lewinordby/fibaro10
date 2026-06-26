import React from "react";
import ReactDOM from "react-dom/client";
import { App as AntApp, ConfigProvider } from "antd";
import nbNO from "antd/locale/nb_NO";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { antdTheme } from "./designTokens";
import "./styles/tokens.css";
import "./styles/layout.css";
import "./styles/build.css";
import "./styles/module-content.css";
import "./styles/status.css";
import "./styles/timelines.css";
import "./styles/ventilation.css";
import "./styles/energy.css";
import "./styles/records.css";
import "./styles/mobile-preview.css";
import "./styles/responsive.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
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
  </React.StrictMode>,
);
