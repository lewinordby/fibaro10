import { defaultModuleView, MODULE_VIEWS } from "./moduleViews";

function cleanPath(href: string): string {
  try {
    const url = new URL(href, window.location.origin);
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return href;
  }
}

export function appPath(href?: string): string | null {
  if (!href) return null;
  const path = cleanPath(href);
  if (path === "/") return "/";
  if (!path.startsWith("/")) return null;

  const pathname = path.split(/[?#]/, 1)[0];
  const parts = pathname.split("/").filter(Boolean);
  const module = parts[0];
  const view = parts[1] || defaultModuleView(module);

  if (module === "status") {
    return ["oversikt", "sammenligning"].includes(view) ? path : null;
  }

  const moduleViews = MODULE_VIEWS[module];
  if (!moduleViews) return null;

  if (module === "parkering" && view === "oppgjor" && parts[2]) return path;
  if (module === "parkering" && view === "kjoretoy" && parts[2]) return path;
  if (moduleViews.some((item) => item.key === view)) return path;
  return null;
}
