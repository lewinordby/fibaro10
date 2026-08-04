import { useEffect, useMemo, useState } from "react";
import { domainApi } from "../api";
import { displayCell, valueLabel } from "../format";
import { useApi } from "../hooks";
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

function CompactTable({ columns, rows }: { columns: string[]; rows: JsonRecord[] }) {
  return <div className="overflow-x-auto"><table className="w-full table-auto"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/40"><tr>{columns.map((column) => <th className="whitespace-nowrap px-4 py-3 text-left font-semibold" key={column}>{valueLabel(column)}</th>)}</tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{rows.map((row, index) => <tr className="hover:bg-gray-50/60 dark:hover:bg-gray-700/20" key={String(row.id || index)}>{columns.map((column) => <td className="whitespace-nowrap px-4 py-3 tabular-nums" key={column}>{column.endsWith("_at") || column === "timestamp" || column === "begin_at" || column === "end_at" ? stamp(row[column]) : displayCell(column, row[column])}</td>)}</tr>)}{!rows.length ? <tr><td className="px-5 py-8 text-center text-sm text-gray-400" colSpan={columns.length}>Ingen data mottatt</td></tr> : null}</tbody></table></div>;
}

function RobotList({ robots, selected, select }: { robots: RoborockRobotSummary[]; selected: string; select: (duid: string) => void }) {
  return <Panel title="Robotvaskere" subtitle={`${robots.length} registrert`}><div className="divide-y divide-gray-100 dark:divide-gray-700/60">{robots.map((robot) => {
    const problem = Boolean(robot.last_error || (robot.error_code && robot.error_code !== 0) || robot.cloud_online === false);
    return <button className={`grid w-full grid-cols-[2.25rem_1fr_auto] items-center gap-3 px-4 py-4 text-left ${selected === robot.duid ? "bg-green-500/10" : "hover:bg-gray-50 dark:hover:bg-gray-700/20"}`} onClick={() => select(robot.duid)} key={robot.duid}><span className={`flex h-9 w-9 items-center justify-center rounded-full ${problem ? "bg-red-500/10 text-red-500" : "bg-green-500/10 text-green-600"}`}><MosaicIcon name="robot" size={18} /></span><span className="min-w-0"><strong className="block truncate text-sm text-gray-800 dark:text-gray-100">{robot.name}</strong><small className="block truncate text-gray-400">{robot.state_name || robot.model || "Ingen status"} · {robot.battery == null ? "-" : `${robot.battery}%`}</small></span><span className={`h-2.5 w-2.5 rounded-full ${problem ? "bg-red-500" : robot.cloud_online === false ? "bg-gray-400" : "bg-green-500"}`} title={problem ? "Krever kontroll" : "OK"} /></button>;
  })}</div></Panel>;
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
  return <div className="space-y-5">
    <Panel title={String(robot.name || summary?.name || "Robot")} subtitle={`${String(robot.model || metadata.model || "Ukjent modell")} · sist sett ${stamp(robot.last_seen_at)}`} actions={<button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={result.reload}><MosaicIcon name="refresh" />Oppdater</button>}><div className="grid grid-cols-2 gap-3 p-5 lg:grid-cols-4"><MetricCard label="Status" value={String(status.state_label || status.state_name || "-")} detail={stamp(status.timestamp)} tone="green" /><MetricCard label="Batteri" value={status.battery == null ? "-" : Number(status.battery)} unit={status.battery == null ? "" : "%"} detail={String(status.charge_label || "Ladestatus ukjent")} tone="green" /><MetricCard label="Feil" value={String(status.error_label || "-")} detail={String(robot.last_error || "Ingen siste melding")} tone={Number(status.error_code || 0) ? "red" : "gray"} /><MetricCard label="WiFi" value={String(status.signal_label || "-")} detail={String(robot.local_ip || status.local_ip || "Ingen lokal IP")} tone="sky" /></div></Panel>
    <div className="grid gap-5 xl:grid-cols-2"><Panel title="Robotdata" subtitle="Teknisk identitet"><div className="px-5 py-2"><Field label="Navn" value={robot.name} /><Field label="DUID" value={robot.duid} /><Field label="Serienummer" value={robot.serial_number || metadata.sn} /><Field label="Produkt-ID" value={metadata.product_id || robot.product} /><Field label="Modell" value={robot.model || metadata.model} /><Field label="Firmware" value={robot.firmware || metadata.fv} /><Field label="Protokoll" value={robot.protocol_version || metadata.pv} /><Field label="Tidssone" value={robot.time_zone_id || metadata.time_zone_id} /><Field label="Cloud" value={robot.cloud_label} /><Field label="Delt" value={robot.shared_label} /></div></Panel><Panel title="Nettverk og siste status" subtitle="Lokal LAN-lesing"><div className="px-5 py-2"><Field label="Lokal IP" value={robot.local_ip || status.local_ip} /><Field label="SSID" value={network.ssid} /><Field label="MAC" value={network.mac} /><Field label="Aksesspunkt" value={network.bssid} /><Field label="Sist lokal" value={stamp(robot.last_local_at)} /><Field label="Rengjøringstid" value={status.clean_time_seconds == null ? "-" : `${Math.round(Number(status.clean_time_seconds) / 60)} min`} /><Field label="Areal" value={status.clean_area_m2 == null ? "-" : `${status.clean_area_m2} m²`} /><Field label="Sugekraft" value={status.fan_label} /><Field label="Mopp" value={status.mop_label} /></div></Panel></div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(20rem,0.7fr)]"><Panel title="Siste kart" subtitle={data.latestMap ? `${stamp(data.latestMap.timestamp)} · ${displayCell("rooms", data.latestMap.rooms)} rom` : "Ikke mottatt"}><div className="p-5">{data.latestMap?.imageDataUrl ? <img className="max-h-[34rem] w-full rounded-lg bg-gray-900 object-contain" src={data.latestMap.imageDataUrl} alt={`Kart for ${String(robot.name || "robot")}`} /> : <div className="flex h-56 items-center justify-center rounded-lg bg-gray-50 text-sm text-gray-400 dark:bg-gray-900/30">Ingen kart er mottatt</div>}</div></Panel><Panel title="Forbruksdeler" subtitle={consumables.timestamp ? stamp(consumables.timestamp) : "Ikke mottatt"}><div className="px-5 py-2"><Field label="Hovedbørste brukt" value={consumables.main_brush} /><Field label="Sidebørste brukt" value={consumables.side_brush} /><Field label="Filter brukt" value={consumables.filter} /><Field label="Sensor siden rens" value={consumables.sensor} /><Field label="Støvtømming" value={consumables.dust_collection} /></div></Panel></div>
    <Panel title="Planlagte jobber" subtitle={`${data.schedules.length} planer`}><CompactTable columns={["schedule_label", "cron", "segments", "rounds_label", "fan_label", "mop_label", "water_label", "enabled_label"]} rows={data.schedules} /></Panel>
    <Panel title="Siste rengjøringer" subtitle={`${data.jobs.length} jobber`}><CompactTable columns={["begin_at", "end_at", "duration_minutes", "cleaned_area_m2", "rounds_label", "complete_label", "error_label"]} rows={data.jobs} /></Panel>
    <Panel title="Statushistorikk" subtitle={`${data.statuses.length} samples`}><CompactTable columns={["timestamp", "state_label", "battery", "fan_label", "mop_label", "signal_label", "local_ip"]} rows={data.statuses.slice(0, 30)} /></Panel>
  </div>;
}

export function RoborockSpecial({ data }: { data: RoborockModuleData }) {
  const robots = useMemo(() => data.robots || [], [data.robots]);
  const [selected, setSelected] = useState(robots[0]?.duid || "");
  useEffect(() => { if (!robots.some((robot) => robot.duid === selected)) setSelected(robots[0]?.duid || ""); }, [robots, selected]);
  return <div className="grid items-start gap-5 xl:grid-cols-[20rem_minmax(0,1fr)]"><RobotList robots={robots} selected={selected} select={setSelected} />{selected ? <RobotDetail duid={selected} summary={robots.find((robot) => robot.duid === selected)} /> : <Panel><div className="p-8 text-sm text-gray-400">Ingen roboter er registrert.</div></Panel>}</div>;
}
