import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "@lilletorget/microapp-ui/primitives";
import { AppRouter } from "@lilletorget/microapp-ui/router";
import App from "./App";
import "@lilletorget/mosaic-theme/font.css";
import "./style.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AppRouter>
        <App />
      </AppRouter>
    </ThemeProvider>
  </StrictMode>,
);
