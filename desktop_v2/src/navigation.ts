export function appPath(href?: string): string | null {
  if (!href) return null;
  if (href === "/v2") return "/";
  if (href.startsWith("/v2/")) return href.slice(3);
  return null;
}

export function legacyPath(href: string): string {
  return `/klassisk?path=${encodeURIComponent(href)}`;
}

export function shouldOpenInLegacyFrame(href: string): boolean {
  if (!href.startsWith("/") || href.startsWith("/v2")) return false;
  if (href.startsWith("/api/") || href === "/health") return false;
  if (href.endsWith("/json") || href.endsWith("/download") || href.endsWith("/pdf")) return false;
  if (href === "/download" || href.includes(".csv") || href.includes(".pdf")) return false;
  return true;
}
