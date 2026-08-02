import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

type Theme = "light" | "dark";
type ThemeContextValue = { currentTheme: Theme; changeCurrentTheme: (theme: Theme) => void };

const ThemeContext = createContext<ThemeContextValue | null>(null);

function initialTheme(): Theme {
  const persisted = window.localStorage.getItem("theme");
  if (persisted === "light" || persisted === "dark") return persisted;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [currentTheme, setCurrentTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.classList.add("**:transition-none!");
    document.documentElement.classList.toggle("dark", currentTheme === "dark");
    document.documentElement.style.colorScheme = currentTheme;
    const timeout = window.setTimeout(() => document.documentElement.classList.remove("**:transition-none!"), 1);
    return () => window.clearTimeout(timeout);
  }, [currentTheme]);

  useEffect(() => {
    if (window.localStorage.getItem("theme")) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setCurrentTheme(media.matches ? "dark" : "light");
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const value = useMemo(() => ({
    currentTheme,
    changeCurrentTheme: (theme: Theme) => {
      window.localStorage.setItem("theme", theme);
      setCurrentTheme(theme);
    },
  }), [currentTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useThemeProvider() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("ThemeProvider mangler");
  return context;
}
