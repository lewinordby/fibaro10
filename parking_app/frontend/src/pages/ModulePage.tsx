import { api } from "../api";
import { ModuleContent } from "../components/ModuleContent";
import { ErrorState, Loading } from "../components/PageState";
import { useApi } from "../hooks";
import { useAppLocation } from "../router";

export default function ModulePage({ view }: { view: string }) {
  const { search } = useAppLocation();
  const params = new URLSearchParams(search);
  const result = useApi(() => api.module(view, params), `module-${view}-${search}`);
  const config = useApi(api.config, "app-config-module");
  if (result.loading || config.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  return <ModuleContent data={result.data} reload={result.reload} fibaroUrl={config.data?.fibaro10AppUrl || "http://192.168.20.218:8110"} />;
}
