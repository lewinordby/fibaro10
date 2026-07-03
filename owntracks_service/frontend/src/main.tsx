import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider } from "antd";
import App from "./App";
import "./styles.css";

const theme = {
  token: {
    colorPrimary: "#2563eb",
    colorSuccess: "#15803d",
    colorWarning: "#f59e0b",
    colorError: "#b91c1c",
    borderRadius: 8,
    colorText: "#111827",
    colorTextSecondary: "#64748b",
    colorBorder: "#e2e8f0",
    colorBgLayout: "#f4f7fb",
    colorBgContainer: "#ffffff",
    controlHeight: 32,
    fontSize: 13,
    fontSizeSM: 12,
    lineHeight: 1.35,
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  components: {
    Button: {
      borderRadius: 7,
      controlHeight: 32,
      fontWeight: 650,
    },
    Card: {
      borderRadiusLG: 8,
      paddingLG: 12,
      headerHeight: 38,
    },
    Layout: {
      bodyBg: "#f4f7fb",
      siderBg: "#ffffff",
      triggerBg: "#ffffff",
    },
    Menu: {
      itemBorderRadius: 7,
      itemHeight: 36,
    },
    Select: {
      borderRadius: 7,
    },
    Table: {
      borderColor: "#e8edf4",
      headerBg: "#f8fafc",
      headerColor: "#475569",
      rowHoverBg: "#f8fbff",
      cellFontSize: 12,
      cellFontSizeSM: 11,
      cellPaddingBlock: 7,
      cellPaddingInline: 9,
      headerSplitColor: "#e8edf4",
    },
    Tag: {
      borderRadiusSM: 6,
    },
  },
} as const;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider theme={theme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
