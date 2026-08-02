import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { AppRouter } from "./router";
import { ThemeProvider } from "./components/ThemeContext";
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
