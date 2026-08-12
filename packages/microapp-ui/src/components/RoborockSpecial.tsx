import { domainApi } from "../api";
import { displayCell, valueLabel } from "../format";
import { useApi } from "../hooks";
import { AppLink, useAppLocation } from "../router";
import type { JsonRecord, RoborockModuleData, RoborockRobotDetail, RoborockRobotSummary } from "../types";
import { MetricCard, Panel } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";

function stamp(value: unknown) {
  if (!value) return "-";
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString("nb-NO", { timeZone: "Europe/Oslo" });
}

function Field({ label, value }: { label: string; value: unknown }) {
  return <div className="flex items-start justify-between gap-4 border-b border-gray-100 py-2.5 text-sm last:border-0 dark:border-gray-700/70"><span className="text-gray-400">{label}</span><strong className="max-w-[65%] text-right font-medium text-gray-700 dark:text-gray-200">{displayCell(label, value)}</strong></div>;
}

function telemetryTone(value: unknown) {
  const text = String(value ?? "").toLocaleLowerCase("nb-NO");
  if (["ikke støttet", "-"].includes(text)) return "text-gray-400";
  if (["ok", "ingen feil", "nei", "0"].includes(text)) return "text-green-600 dark:text-green-400";
  if (text.includes("full") || text.includes("tom") || text.includes("feil") || text.includes("mangler")) return "text-red-500";
  return "text-gray-700 dark:text-gray-200";
}

function TelemetryFields({ fields }: { fields: RoborockRobotDetail["telemetryFields"] }) {
  const groups = [...new Set(fields.map((field) => field.category))];
  return <div className="grid gap-x-8 px-5 py-3 lg:grid-cols-2">{groups.map((group) => <section key={group}><h3 className="border-b border-gray-100 py-3 text-xs font-semibold uppercase text-gray-400 dark:border-gray-700/70">{group}</h3>{fields.filter((field) => field.category === group).map((field) => <div className="flex items-start justify-between gap-4 border-b border-gray-100 py-2.5 text-sm last:border-0 dark:border-gray-700/70" key={field.field}><span className="text-gray-500 dark:text-gray-400">{field.label}</span><span className={`max-w-[58%] text-right font-medium ${field.supported ? telemetryTone(field.valueLabel) : "text-gray-400"}`}>{field.valueLabel}</span></div>)}</section>)}</div>;
}

function JsonValue({ value }: { value: unknown }) {
  const text = value == null ? "-" : typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-50 p-3 text-xs text-gray-600 dark:bg-gray-900/50 dark:text-gray-300">{text}</pre>;
}

function TelemetryProbes({ probes }: { probes: RoborockRobotDetail["telemetryProbes"] }) {
  return <div className="divide-y divide-gray-100 dark:divide-gray-700/60">{probes.map((probe) => <details className="group px-5 py-3" key={probe.command}><summary className="grid cursor-pointer list-none grid-cols-[1fr_auto] items-center gap-3 text-sm"><span><strong className="font-medium text-gray-700 dark:text-gray-200">{probe.command}</strong><small className="mt-0.5 block text-gray-400">{probe.checkedAt ? stamp(probe.checkedAt) : "Ikke kontrollert"}{probe.resultType ? ` · ${probe.resultType}` : ""}</small></span><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${probe.supported ? "bg-green-500/10 text-green-600 dark:text-green-400" : probe.status === "Ikke støttet" ? "bg-gray-500/10 text-gray-500" : "bg-red-500/10 text-red-500"}`}>{probe.status}</span></summary><div className="mt-3">{probe.error ? <p className="mb-2 text-sm text-red-500">{probe.error}</p> : null}<JsonValue value={probe.value} /></div></details>)}</div>;
}

function CompactTable({ columns, rows }: { columns: string[]; rows: JsonRecord[] }) {
  return <div className="overflow-x-auto"><table className="w-full table-auto"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/40"><tr>{columns.map((column) => <th className="whitespace-nowrap px-4 py-3 text-left font-semibold" key={column}>{valueLabel(column)}</th>)}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{rows.map((row, index) => <tr className="hover:bg-gray-50/60 dark:hover:bg-gray-700/20" key={String(row.id || index)}>{columns.map((column) => <td className="whitespace-nowrap px-4 py-3 tabular-nums" key={column}>{column.endsWith("_at") || column === "timestamp" || column === "begin_at" || column === "end_at" ? stamp(row[column]) : displayCell(column, row[column])}</td>)}</tr>)}{!rows.length ? <tr><td className="px-5 py-8 text-center text-sm text-gray-400" colSpan={columns.length}>Ingen data mottatt</td></tr> : null}</tbody></table></div>;
}

function RobotOverview({ robots }: { robots: RoborockRobotSummary[] }) {
  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Robotvaskere</h2><p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Siste kjente status for alle registrerte roboter.</p></div>
      <span className="text-sm font-medium tabular-nums text-gray-500 dark:text-gray-400">{robots.length} registrert</span>
    </div>
    <div className="grid gap-5 md:grid-cols-2">{robots.map((robot) => {
      const problem = Boolean(robot.last_error || (robot.error_code && robot.error_code !== 0) || robot.cloud_online === false);
      const state = robot.state_name || "Ingen status";
      return <AppLink className="group overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xs transition hover:border-green-400 hover:shadow-md dark:border-gray-700/60 dark:bg-gray-800 dark:hover:border-green-500/70" to={`/renhold/robot/${encodeURIComponent(robot.duid)}`} key={robot.duid}>
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-5 py-4 dark:border-gray-700/60">
          <span className="flex min-w-0 items-center gap-3"><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${problem ? "bg-red-500/10 text-red-500" : "bg-green-500/10 text-green-600 dark:text-green-400"}`}><MosaicIcon name="robot" size={20} /></span><span className="min-w-0"><strong className="block truncate text-base font-semibold text-gray-800 dark:text-gray-100">{robot.name}</strong><small className="block truncate text-gray-400">{robot.model || "Ukjent modell"}</small></span></span>
          <span className={`mt-1 inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${problem ? "bg-red-500/10 text-red-600 dark:text-red-400" : "bg-green-500/10 text-green-700 dark:text-green-400"}`}><span className={`h-2 w-2 rounded-full ${problem ? "bg-red-500" : "bg-green-500"}`} />{problem ? "Kontroller" : "OK"}</span>
        </div>
        <div className="grid grid-cols-2 divide-x divide-gray-100 px-2 py-4 dark:divide-gray-700/60">
          <div className="px-3"><span className="block text-xs font-semibold uppercase text-gray-400">Status</span><strong className="mt-1 block truncate text-sm font-medium text-gray-700 dark:text-gray-200">{state}</strong></div>
          <div className="px-3"><span className="block text-xs font-semibold uppercase text-gray-400">Batteri</span><strong className="mt-1 block text-sm font-medium tabular-nums text-gray-700 dark:text-gray-200">{robot.battery == null ? "-" : `${robot.battery} %`}</strong></div>
        </div>
        <div className="flex items-center justify-between gap-4 bg-gray-50 px-5 py-3 text-xs text-gray-500 dark:bg-gray-900/30 dark:text-gray-400"><span className="truncate">Sist lest {stamp(robot.status_at || robot.last_seen_at)}</span><span className="flex shrink-0 items-center gap-1 font-medium text-green-700 dark:text-green-400">Detaljer <MosaicIcon name="arrow-right" size={14} /></span></div>
        {robot.last_error ? <div className="border-t border-red-100 bg-red-50 px-5 py-2.5 text-xs text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400">{robot.last_error}</div> : null}
      </AppLink>;
    })}</div>
    {!robots.length ? <Panel><div className="p-8 text-sm text-gray-400">Ingen roboter er registrert.</div></Panel> : null}
  </div>;
}

function RobotDetail({ duid, summary }: { duid: string; summary?: RoborockRobotSummary }) {
  const result = useApi(() => domainApi.get<RoborockRobotDetail>(`/api/renhold/robots/${encodeURIComponent(duid)}`), `roborock-${duid}`);
  if (result.loading && !result.data) return <Panel><div className="p-8 text-sm text-gray-400">Henter robotdetaljer ...</div></Panel>;
  if (result.error || !result.data) return <Panel><div className="flex items-center justify-between gap-3 p-6 text-sm text-red-500"><span>{result.error?.message || "Kunne ikke hente roboten"}</span><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}>Prøv igjen</button></div></Panel>;
  const data = result.data;
  const robot = data.robot;
  const status = data.latestStatus || {};
  const metadata = data.metadata || {};
  const network = data.network || {};
  const consumables = data.consumables || {};
  const telemetry = data.latestTelemetry || {};
  const telemetryFields = data.telemetryFields || [];
  const supportedProbes = (data.telemetryProbes || []).filter((probe) => probe.supported).length;
  return <div className="space-y-5">
    <Panel title={String(robot.name || summary?.name || "Robot")} subtitle={`${String(robot.model || metadata.model || "Ukjent modell")} · telemetri ${stamp(telemetry.timestamp || robot.last_seen_at)}`} actions={<button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}><MosaicIcon name="refresh" />Oppdater</button>}><div className="grid grid-cols-2 gap-3 p-5 lg:grid-cols-4"><MetricCard label="Status" value={String(telemetry.state_label || status.state_label || status.state_name || "-")} detail={stamp(telemetry.timestamp || status.timestamp)} tone="green" /><MetricCard label="Batteri" value={telemetry.battery == null ? status.battery == null ? "-" : Number(status.battery) : Number(telemetry.battery)} unit={telemetry.battery == null && status.battery == null ? "" : "%"} detail={String(telemetry.charge_label || status.charge_label || "Ladestatus ukjent")} tone="green" /><MetricCard label="Rentvann" value={String(telemetry.clear_water_label || "Ikke støttet")} detail={String(telemetry.dirty_water_label ? `Skittent vann: ${telemetry.dirty_water_label}` : "Ingen tankdata")} tone={String(telemetry.clear_water_label || "OK") === "OK" ? "sky" : "red"} /><MetricCard label="Dokk" value={String(telemetry.dock_error_label || "Ikke mottatt")} detail={String(telemetry.dock_label || robot.last_error || "Ingen dokkdata")} tone={Number(telemetry.dock_error_status || 0) ? "red" : "gray"} /></div></Panel>
    <Panel title="Alle telemetriverdier" subtitle={telemetry.timestamp ? `Sist lest ${stamp(telemetry.timestamp)}` : "Venter på første telemetrimåling"}>{telemetryFields.length ? <TelemetryFields fields={telemetryFields} /> : <div className="p-8 text-sm text-gray-400">Ingen telemetri er mottatt ennå.</div>}</Panel>
    <Panel title="Tilstandsendringer" subtitle={`${data.telemetryEvents.length} siste hendelser`}><CompactTable columns={["timestamp", "title", "previous_label", "current_label", "severity"]} rows={data.telemetryEvents} /></Panel>
    <Panel title="Telemetrilogg" subtitle={`${data.telemetrySamples.length} minuttmålinger`}><CompactTable columns={["timestamp", "state_label", "battery", "charge_label", "clear_water_label", "dirty_water_label", "dust_bag_label", "dock_error_label"]} rows={data.telemetrySamples.slice(0, 120)} /></Panel>
    <Panel title="API-dekning" subtitle={`${supportedProbes}/${data.telemetryProbes.length} lesekall støttes av denne modellen`}>{data.telemetryProbes.length ? <TelemetryProbes probes={data.telemetryProbes} /> : <div className="p-8 text-sm text-gray-400">Venter på første fullstendige API-kontroll.</div>}</Panel>
    <Panel title="Komplett råstatus" subtitle={`${data.rawStatusFields.length} felter fra GET_STATUS`}><CompactTable columns={["field", "value"]} rows={data.rawStatusFields} /></Panel>
    <div className="grid gap-5 xl:grid-cols-2"><Panel title="Robotdata" subtitle="Teknisk identitet"><div className="px-5 py-2"><Field label="Navn" value={robot.name} /><Field label="DUID" value={robot.duid} /><Field label="Serienummer" value={robot.serial_number || metadata.sn} /><Field label="Produkt-ID" value={metadata.product_id || robot.product} /><Field label="Modell" value={robot.model || metadata.model} /><Field label="Firmware" value={robot.firmware || metadata.fv} /><Field label="Protokoll" value={robot.protocol_version || metadata.pv} /><Field label="Tidssone" value={robot.time_zone_id || metadata.time_zone_id} /><Field label="Cloud" value={robot.cloud_label} /><Field label="Delt" value={robot.shared_label} /></div></Panel><Panel title="Nettverk og siste status" subtitle="Lokal LAN-lesing"><div className="px-5 py-2"><Field label="Lokal IP" value={robot.local_ip || status.local_ip} /><Field label="SSID" value={network.ssid} /><Field label="MAC" value={network.mac} /><Field label="Aksesspunkt" value={network.bssid} /><Field label="Sist lokal" value={stamp(robot.last_local_at)} /><Field label="Rengjøringstid" value={status.clean_time_seconds == null ? "-" : `${Math.round(Number(status.clean_time_seconds) / 60)} min`} /><Field label="Areal" value={status.clean_area_m2 == null ? "-" : `${status.clean_area_m2} m²`} /><Field label="Sugekraft" value={status.fan_label} /><Field label="Mopp" value={status.mop_label} /></div></Panel></div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(20rem,0.7fr)]"><Panel title="Siste kart" subtitle={data.latestMap ? `${stamp(data.latestMap.timestamp)} · ${displayCell("rooms", data.latestMap.rooms)} rom` : "Ikke mottatt"}><div className="p-5">{data.latestMap?.imageDataUrl ? <img className="max-h-[34rem] w-full rounded-lg bg-gray-900 object-contain" src={data.latestMap.imageDataUrl} alt={`Kart for ${String(robot.name || "robot")}`} /> : <div className="flex h-56 items-center justify-center rounded-lg bg-gray-50 text-sm text-gray-400 dark:bg-gray-900/30">Ingen kart er mottatt</div>}</div></Panel><Panel title="Forbruksdeler" subtitle={consumables.timestamp ? stamp(consumables.timestamp) : "Ikke mottatt"}><div className="px-5 py-2"><Field label="Hovedbørste brukt" value={consumables.main_brush} /><Field label="Sidebørste brukt" value={consumables.side_brush} /><Field label="Filter brukt" value={consumables.filter} /><Field label="Sensor siden rens" value={consumables.sensor} /><Field label="Støvtømming" value={consumables.dust_collection} /></div></Panel></div>
    <Panel title="Planlagte jobber" subtitle={`${data.schedules.length} planer`}><CompactTable columns={["schedule_label", "cron", "segments", "rounds_label", "fan_label", "mop_label", "water_label", "enabled_label"]} rows={data.schedules} /></Panel>
    <Panel title="Siste rengjøringer" subtitle={`${data.jobs.length} jobber`}><CompactTable columns={["begin_at", "end_at", "duration_minutes", "cleaned_area_m2", "rounds_label", "complete_label", "error_label"]} rows={data.jobs} /></Panel>
    <Panel title="Statushistorikk" subtitle={`${data.statuses.length} samples`}><CompactTable columns={["timestamp", "state_label", "battery", "fan_label", "mop_label", "signal_label", "local_ip"]} rows={data.statuses.slice(0, 30)} /></Panel>
  </div>;
}

export function RoborockSpecial({ data }: { data: RoborockModuleData }) {
  const { pathname } = useAppLocation();
  const robots = data.robots || [];
  const match = pathname.match(/^\/renhold\/robot\/([^/]+)$/);
  const selected = match ? decodeURIComponent(match[1]) : "";
  const summary = robots.find((robot) => robot.duid === selected);
  if (!selected) return <RobotOverview robots={robots} />;
  if (!summary) return <Panel title="Robot ikke funnet"><div className="p-8 text-sm text-gray-400">Roboten finnes ikke lenger i den registrerte robotlisten.</div></Panel>;
  return <RobotDetail duid={selected} summary={summary} />;
}
