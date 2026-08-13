import { domainApi } from "@lilletorget/microapp-ui/api";
import type { SunSessionImageBrowser } from "./types";

export function fetchSunSessionImages(sessionId: number, snapshotId?: string | null) {
  const params = new URLSearchParams();
  if (snapshotId) params.set("snapshot_id", snapshotId);
  const query = params.toString();
  return domainApi.get<SunSessionImageBrowser>(`/api/soling/enkeltimer/${encodeURIComponent(sessionId)}/image-browser${query ? `?${query}` : ""}`);
}

export async function selectSunSessionImage(sessionId: number, snapshotId: string) {
  const params = new URLSearchParams({ snapshot_id: snapshotId });
  const result = await domainApi.mutate<SunSessionImageBrowser | { browser: SunSessionImageBrowser }>(`/api/soling/enkeltimer/${encodeURIComponent(sessionId)}/image?${params}`, "POST");
  return "browser" in result ? result.browser : result;
}
