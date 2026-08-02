import { createContext, type MouseEvent, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

type RouterValue = {
  pathname: string;
  search: string;
  navigate: (target: string, replace?: boolean) => void;
};

const RouterContext = createContext<RouterValue | null>(null);

function currentLocation() {
  return { pathname: window.location.pathname || "/", search: window.location.search || "" };
}

export function AppRouter({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState(currentLocation);
  useEffect(() => {
    const onPopState = () => setLocation(currentLocation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  const navigate = useCallback((target: string, replace = false) => {
    const next = new URL(target, window.location.origin);
    if (next.origin !== window.location.origin) {
      window.location.assign(next.href);
      return;
    }
    const nextTarget = `${next.pathname}${next.search}${next.hash}`;
    if (replace) window.history.replaceState({}, "", nextTarget);
    else window.history.pushState({}, "", nextTarget);
    setLocation(currentLocation());
    window.scrollTo({ top: 0, behavior: "auto" });
  }, []);
  const value = useMemo(() => ({ ...location, navigate }), [location, navigate]);
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useAppLocation() {
  const value = useContext(RouterContext);
  if (!value) throw new Error("useAppLocation må brukes innenfor AppRouter");
  return value;
}

export function AppLink({ to, className, children }: { to: string; className?: string; children: ReactNode }) {
  const { navigate } = useAppLocation();
  function onClick(event: MouseEvent<HTMLAnchorElement>) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  }
  return <a href={to} className={className} onClick={onClick}>{children}</a>;
}

export function useAppSearchParams() {
  const { pathname, search, navigate } = useAppLocation();
  const params = useMemo(() => new URLSearchParams(search), [search]);
  const setParams = useCallback((next: URLSearchParams, replace = false) => {
    const query = next.toString();
    navigate(`${pathname}${query ? `?${query}` : ""}`, replace);
  }, [navigate, pathname]);
  return [params, setParams] as const;
}

