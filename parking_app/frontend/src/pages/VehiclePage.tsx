import { displayCell } from "@lilletorget/microapp-ui/format";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { ErrorState, Loading, Panel } from "@lilletorget/microapp-ui/primitives";
import { AppLink } from "@lilletorget/microapp-ui/router";
import { api } from "../api";
import { DataTable, ModuleActions, ModuleCards } from "../components/ModuleContent";

export default function VehiclePage({ plate }: { plate: string }) {
  const result = useApi(() => api.vehicle(plate), `vehicle-${plate}`);
  const config = useApi(api.config, "app-config-vehicle");
  if (result.loading || config.loading) return <Loading />;
  if (result.error || !result.data) return <ErrorState error={result.error} onRetry={result.reload} />;
  const data = result.data;
  const columns = data.sessions.length ? Object.keys(data.sessions[0]).filter((key) => !["id", "path", "unifi_start_url", "unifi_end_url", "owner_warning", "parking_area", "source_system", "user_interface", "subtype", "vehicle_make", "vehicle_type", "vehicle_color", "vehicle_owner", "omrade"].includes(key)) : [];
  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><span className="text-sm text-gray-500">Registreringsnummer</span><h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">{data.plate}</h2><p className="text-sm text-gray-500">{data.subtitle}</p></div><AppLink className="btn border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" to="/kjoretoy">Tilbake til kjøretøy</AppLink></div>
    <ModuleActions actions={data.actions} onComplete={result.reload} />
    <ModuleCards cards={data.cards} />
    {data.warnings.length ? <Panel title="Merknader"><div className="space-y-2 p-5">{data.warnings.map((warning) => <div className="rounded-lg bg-yellow-500/10 px-4 py-3 text-sm text-yellow-700 dark:text-yellow-300" key={warning}>{warning}</div>)}</div></Panel> : null}
    <Panel title="Kjøretøy og eier"><dl className="grid grid-cols-1 gap-x-8 sm:grid-cols-2 xl:grid-cols-4">{data.fields.map((field) => <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700/60" key={field.label}><dt className="text-xs font-semibold uppercase text-gray-400">{field.label}</dt><dd className="mt-1 font-medium text-gray-800 dark:text-gray-100">{displayCell(field.label.toLowerCase(), field.value)}</dd>{field.detail ? <p className="mt-1 text-xs text-gray-500">{field.detail}</p> : null}</div>)}</dl></Panel>
    <DataTable table={{ title: "Alle parkeringer", columns, rows: data.sessions, meta: { totalRows: data.sessions.length, disablePagination: true } }} fibaroUrl={config.data?.fibaro10AppUrl || "http://192.168.20.218:8110"} />
  </div>;
}
