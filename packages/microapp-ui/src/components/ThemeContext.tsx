import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

type Theme = "light" | "dark";
type ThemeValue = { currentTheme: Theme; changeCurrentTheme: (theme: Theme) => void };

const ThemeContext = createContext<ThemeValue | null>(null);

function systemTheme(): Theme {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function storedTheme(): Theme | null {
  const value = window.localStorage.getItem("theme");
  return value === "light" || value === "dark" ? value : null;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [currentTheme, setCurrentTheme] = useState<Theme>(() => storedTheme() ?? systemTheme());

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", currentTheme === "dark");
    root.style.colorScheme = currentTheme;
  }, [currentTheme]);

  useEffect(() => {
    if (storedTheme()) return;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setCurrentTheme(query.matches ? "dark" : "light");
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  const value = useMemo<ThemeValue>(() => ({
    currentTheme,
    changeCurrentTheme: (theme) => {
      window.localStorage.setItem("theme", theme);
      setCurrentTheme(theme);
    },
  }), [currentTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme må brukes innenfor ThemeProvider");
  return context;
}
