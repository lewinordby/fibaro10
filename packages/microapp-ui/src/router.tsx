import { createContext, type AnchorHTMLAttributes, type MouseEvent, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { removeCurrentAppBasePath, withCurrentAppBasePath } from "./navigation";

type RouterValue = {
  pathname: string;
  search: string;
  navigate: (target: string, replace?: boolean) => void;
};

const RouterContext = createContext<RouterValue | null>(null);

function currentLocation() {
  return { pathname: removeCurrentAppBasePath(window.location.pathname || "/"), search: window.location.search || "" };
}

export function AppRouter({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState(currentLocation);
  useEffect(() => {
    const onPopState = () => setLocation(currentLocation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  const navigate = useCallback((target: string, replace = false) => {
    const scopedTarget = /^https?:\/\//i.test(target) ? target : withCurrentAppBasePath(target);
    const next = new URL(scopedTarget, window.location.origin);
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

type AppLinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & { to: string };

export function AppLink({ to, onClick: onLinkClick, ...props }: AppLinkProps) {
  const { navigate } = useAppLocation();
  function onClick(event: MouseEvent<HTMLAnchorElement>) {
    onLinkClick?.(event);
    if (event.defaultPrevented) return;
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  }
  return <a href={withCurrentAppBasePath(to)} {...props} onClick={onClick} />;
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
