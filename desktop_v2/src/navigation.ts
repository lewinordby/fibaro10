export function appPath(href?: string): string | null {
  if (!href) return null;
  if (href === "/v2") return "/";
  if (href.startsWith("/v2/")) return href.slice(3);
  return null;
}
