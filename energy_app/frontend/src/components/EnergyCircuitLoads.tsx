import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { MosaicIcon, Panel, nok } from "@lilletorget/microapp-ui";
import { domainApi } from "@lilletorget/microapp-ui/api";
import type { JsonRecord } from "@lilletorget/microapp-ui/types";
import type {
  EnergyAggregateLive,
  EnergyCircuit,
  EnergyCircuitLoadsData,
  EnergyLoadItem,
  EnergyNode,
  EnergyNodeLive,
  EnergyNodesLiveResponse,
  Hc3EnergyDevice,
  Hc3EnergyDevicesResponse,
} from "../types";

type NodeType = "zwave_device" | "output" | "child_device" | "meter" | "logical";
type MappingFilter = "all" | "mapped" | "needs-work" | "empty";
type EditorState = { kind: "node" | "load"; circuit: EnergyCircuit; node?: EnergyNode; load?: EnergyLoadItem; parent?: EnergyNode };

const nodeTypes: Array<{ value: NodeType; label: string }> = [
  { value: "zwave_device", label: "Z-Wave-enhet" },
  { value: "output", label: "Utgang / kanal" },
  { value: "child_device", label: "Underenhet" },
  { value: "meter", label: "Målepunkt" },
  { value: "logical", label: "Logisk samling" },
];

const nodeProfiles: Record<NodeType, { description: string; parent: boolean; endpoint: boolean; hc3: boolean; power: "none" | "optional" | "required"; switch: boolean; identity: boolean }> = {
  zwave_device: { description: "Fysisk enhet direkte på kurset, med valgfri måling og bryter.", parent: false, endpoint: false, hc3: true, power: "optional", switch: true, identity: true },
  output: { description: "Kanal på en overordnet enhet, for eksempel Q1 eller 123.1.", parent: true, endpoint: true, hc3: true, power: "optional", switch: true, identity: false },
  child_device: { description: "Egen Z-Wave-enhet koblet etter en annen enhet i kursgrenen.", parent: true, endpoint: false, hc3: true, power: "optional", switch: true, identity: true },
  meter: { description: "Dedikert målepunkt som må kobles til en HC3-enhet med sanntidseffekt.", parent: false, endpoint: false, hc3: true, power: "required", switch: false, identity: true },
  logical: { description: "Grupperingspunkt uten egen HC3-enhet eller levende verdi.", parent: false, endpoint: false, hc3: false, power: "none", switch: false, identity: false },
};

function numberOrNull(value: unknown) {
  if (value === "" || value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function textOrNull(value: unknown) {
  const text = String(value ?? "").trim();
  return text || null;
}

function watt(value: unknown) {
  return value == null || !Number.isFinite(Number(value)) ? "-" : `${nok(Number(value), 0)} W`;
}

function kwh(value: unknown) {
  return value == null || !Number.isFinite(Number(value)) ? "-" : `${nok(Number(value), 1)} kWh`;
}

function checkedTime(value?: string | null) {
  if (!value) return "ikke lest";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function flattenNodes(nodes: EnergyNode[]): EnergyNode[] {
  return nodes.flatMap((node) => [node, ...flattenNodes(node.children || [])]);
}

function nodeOptions(nodes: EnergyNode[], depth = 0, excluded = new Set<number>()): Array<{ id: number; label: string }> {
  return nodes.flatMap((node) => excluded.has(node.id) ? [] : [
    { id: node.id, label: `${"— ".repeat(depth)}${node.name}` },
    ...nodeOptions(node.children || [], depth + 1, excluded),
  ]);
}

function branchPower(node: EnergyNode, live: Record<string, EnergyNodeLive>): number | null {
  const own = live[String(node.id)]?.currentPowerW;
  if (own != null && Number.isFinite(Number(own))) return Number(own);
  const children = (node.children || []).map((child) => branchPower(child, live)).filter((item): item is number => item != null);
  return children.length ? children.reduce((sum, item) => sum + item, 0) : null;
}

function circuitPower(circuit: EnergyCircuit, live: Record<string, EnergyNodeLive>) {
  const values = circuit.nodes.map((node) => branchPower(node, live)).filter((item): item is number => item != null);
  return values.length ? values.reduce((sum, item) => sum + item, 0) : circuit.currentPowerW;
}

function loadPower(load: EnergyLoadItem, measured: boolean) {
  if (load.powerProfile === "variable" && (load.minPowerW != null || load.maxPowerW != null)) {
    return `${load.minPowerW == null ? "-" : nok(load.minPowerW, 0)}–${load.maxPowerW == null ? "-" : nok(load.maxPowerW, 0)} W`;
  }
  return load.expectedPowerW != null ? watt(load.expectedPowerW) : measured ? "Målt samlet" : "Ikke angitt";
}

function Toggle({ checked, label, change }: { checked: boolean; label: string; change: (checked: boolean) => void }) {
  return <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300"><input className="form-checkbox" type="checkbox" checked={checked} onChange={(event) => change(event.target.checked)} />{label}</label>;
}

function EnergyEditor({ state, data, devices, devicesSource, close, saved }: { state: EditorState; data: EnergyCircuitLoadsData; devices: Hc3EnergyDevice[]; devicesSource: string; close: () => void; saved: () => void }) {
  const editing = Boolean(state.node || state.load);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<JsonRecord>(() => state.kind === "node" ? {
    name: state.node?.name || "",
    circuit_no: state.node?.circuitNo ?? state.circuit.circuitNo ?? "",
    parent_node_id: state.node?.parentNodeId ?? state.parent?.id ?? "",
    node_type: state.node?.nodeType || (state.parent ? "output" : "zwave_device"),
    manufacturer: state.node?.manufacturer || "",
    model: state.node?.model || "",
    device_type: state.node?.deviceType || "",
    endpoint_key: state.node?.endpointKey || "",
    area: state.node?.area || state.parent?.area || "",
    hc3_device_id: state.node?.hc3DeviceId ?? "",
    hc3_power_device_id: state.node?.hc3PowerDeviceId ?? "",
    hc3_energy_device_id: state.node?.hc3EnergyDeviceId ?? "",
    hc3_switch_device_id: state.node?.hc3SwitchDeviceId ?? "",
    aggregate_group_key: state.node?.aggregateGroupKey || "",
    active: state.node?.active ?? true,
    note: state.node?.note || "",
  } : {
    name: state.load?.name || "",
    circuit_no: state.load?.energyNodeId != null ? state.circuit.circuitNo ?? "" : state.load?.energyNodeId ?? state.circuit.circuitNo ?? "",
    energy_node_id: state.load?.energyNodeId ?? state.parent?.id ?? "direct",
    load_type: state.load?.loadType || "",
    area: state.load?.area || state.parent?.area || "",
    power_profile: state.load?.powerProfile || (state.load?.expectedPowerW != null ? "fixed" : "unknown"),
    expected_power_w: state.load?.expectedPowerW ?? "",
    min_power_w: state.load?.minPowerW ?? "",
    max_power_w: state.load?.maxPowerW ?? "",
    controllable: state.load?.controllable ?? false,
    critical: state.load?.critical ?? false,
    active: state.load?.active ?? true,
    note: state.load?.note || "",
  });
  const set = (key: string, next: unknown) => setForm((current) => ({ ...current, [key]: next }));
  const selectedCircuit = data.circuits.find((item) => item.circuitNo === numberOrNull(form.circuit_no)) || state.circuit;
  const excluded = new Set(state.node ? flattenNodes([state.node]).map((node) => node.id) : []);
  const placements = nodeOptions(selectedCircuit.nodes || [], 0, excluded);
  const nodeTypeValue = String(form.node_type || "zwave_device");
  const type = (nodeTypeValue in nodeProfiles ? nodeTypeValue : "zwave_device") as NodeType;
  const profile = nodeProfiles[type];
  const selectedMain = devices.find((device) => device.id === numberOrNull(form.hc3_device_id));

  const chooseMainDevice = (raw: string) => {
    const id = numberOrNull(raw);
    const device = devices.find((item) => item.id === id);
    setForm((current) => ({
      ...current,
      hc3_device_id: id ?? "",
      name: textOrNull(current.name) || device?.name || "",
      manufacturer: profile.identity ? textOrNull(current.manufacturer) || device?.manufacturer || "" : "",
      model: profile.identity ? textOrNull(current.model) || device?.model || "" : "",
      device_type: textOrNull(current.device_type) || device?.type || "",
      hc3_power_device_id: device?.hasPower ? device.id : current.hc3_power_device_id,
      hc3_energy_device_id: device?.hasEnergy ? device.id : current.hc3_energy_device_id,
      hc3_switch_device_id: profile.switch && device?.hasSwitch ? device.id : current.hc3_switch_device_id,
    }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (!textOrNull(form.name)) return setError("Navn må fylles ut.");
    if (numberOrNull(form.circuit_no) == null) return setError("Velg kurs.");
    if (state.kind === "node" && profile.parent && numberOrNull(form.parent_node_id) == null) return setError("Velg overordnet enhet.");
    if (state.kind === "node" && profile.endpoint && !textOrNull(form.endpoint_key)) return setError("Fyll inn utgang eller kanal.");
    if (state.kind === "node" && profile.power === "required" && numberOrNull(form.hc3_power_device_id) == null) return setError("Målepunktet må kobles til en HC3-enhet som rapporterer watt.");
    if (state.kind === "load" && form.power_profile === "fixed" && numberOrNull(form.expected_power_w) == null) return setError("Fyll inn effekt for en fast last.");
    if (state.kind === "load" && form.power_profile === "variable" && [form.min_power_w, form.expected_power_w, form.max_power_w].every((item) => numberOrNull(item) == null)) return setError("Fyll inn minst én effektverdi for en variabel last.");
    const min = numberOrNull(form.min_power_w); const normal = numberOrNull(form.expected_power_w); const max = numberOrNull(form.max_power_w);
    if (min != null && max != null && min > max) return setError("Minimum effekt kan ikke være høyere enn maksimum.");
    if (normal != null && min != null && normal < min) return setError("Normal effekt kan ikke være lavere enn minimum.");
    if (normal != null && max != null && normal > max) return setError("Normal effekt kan ikke være høyere enn maksimum.");

    const payload: JsonRecord = state.kind === "node" ? {
      name: textOrNull(form.name), circuit_no: numberOrNull(form.circuit_no), parent_node_id: profile.parent ? numberOrNull(form.parent_node_id) : numberOrNull(form.parent_node_id), node_type: type,
      manufacturer: profile.identity ? textOrNull(form.manufacturer) : null, model: profile.identity ? textOrNull(form.model) : null, device_type: profile.identity || type === "output" ? textOrNull(form.device_type) : null,
      endpoint_key: profile.endpoint ? textOrNull(form.endpoint_key) : null, area: textOrNull(form.area), note: textOrNull(form.note), active: Boolean(form.active),
      hc3_device_id: profile.hc3 ? numberOrNull(form.hc3_device_id) : null, hc3_power_device_id: profile.power === "none" ? null : numberOrNull(form.hc3_power_device_id), hc3_energy_device_id: profile.power === "none" ? null : numberOrNull(form.hc3_energy_device_id),
      hc3_switch_device_id: profile.switch ? numberOrNull(form.hc3_switch_device_id) : null, aggregate_group_key: profile.power !== "none" && numberOrNull(form.hc3_power_device_id) != null ? textOrNull(form.aggregate_group_key) : null,
      has_meter: profile.power !== "none" && numberOrNull(form.hc3_power_device_id) != null, has_switch: profile.switch && numberOrNull(form.hc3_switch_device_id) != null,
    } : {
      name: textOrNull(form.name), circuit_no: numberOrNull(form.circuit_no), energy_node_id: form.energy_node_id === "direct" ? null : numberOrNull(form.energy_node_id), load_type: textOrNull(form.load_type), area: textOrNull(form.area),
      power_profile: form.power_profile || "unknown", expected_power_w: form.power_profile === "unknown" ? null : normal, min_power_w: form.power_profile === "variable" ? min : null, max_power_w: form.power_profile === "variable" ? max : null,
      measured_direct: false, fibaro_device_id: null, fibaro_meter_id: null, zwave_switch_id: null, controllable: Boolean(form.controllable), critical: Boolean(form.critical), active: Boolean(form.active), note: textOrNull(form.note),
    };
    const path = state.kind === "node" ? editing ? `/api/energy/nodes/${state.node?.id}` : "/api/energy/nodes" : editing ? `/api/energy/loads/${state.load?.id}` : "/api/energy/loads";
    setBusy(true);
    try { await domainApi.mutate(path, editing ? "PATCH" : "POST", payload); saved(); close(); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } finally { setBusy(false); }
  };

  const input = (key: string, label: string, typeName = "text", required = false) => <label className="text-sm font-medium text-gray-600 dark:text-gray-300" key={key}>{label}<input className="form-input mt-1 w-full" type={typeName} required={required} value={String(form[key] ?? "")} onChange={(event) => set(key, event.target.value)} /></label>;
  const deviceInput = (key: string, label: string, capability?: "power" | "energy" | "switch") => <label className="text-sm font-medium text-gray-600 dark:text-gray-300">{label}<input className="form-input mt-1 w-full" type="number" list={`hc3-${capability || "all"}`} value={String(form[key] ?? "")} onChange={(event) => key === "hc3_device_id" ? chooseMainDevice(event.target.value) : set(key, event.target.value)} /></label>;
  const circuitSelect = <label className="text-sm font-medium text-gray-600 dark:text-gray-300">Kurs<select className="form-select mt-1 w-full" value={String(form.circuit_no ?? "")} onChange={(event) => setForm((current) => ({ ...current, circuit_no: event.target.value, parent_node_id: "", energy_node_id: "direct" }))}><option value="">Velg kurs</option>{data.circuits.filter((item) => item.circuitNo != null).map((item) => <option value={String(item.circuitNo)} key={item.key}>K{String(item.circuitNo).padStart(2, "0")} · {item.description}</option>)}</select></label>;

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 p-4" role="dialog" aria-modal="true"><form className="max-h-[92dvh] w-full max-w-5xl overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-gray-800" onSubmit={submit}><header className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-100 bg-white px-6 py-4 dark:border-gray-700 dark:bg-gray-800"><div><h2 className="font-semibold text-gray-800 dark:text-gray-100">{editing ? "Rediger" : "Ny"} {state.kind === "node" ? "enhet" : "last"}</h2><p className="mt-0.5 text-xs text-gray-400">{state.circuit.description}</p></div><button type="button" className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={close}>Lukk</button></header>
    <div className="grid gap-6 p-6 lg:grid-cols-2">
      <section className="space-y-4"><h3 className="text-sm font-semibold uppercase text-gray-400">Plassering og identitet</h3>{circuitSelect}
        {state.kind === "node" ? <><label className="text-sm font-medium text-gray-600 dark:text-gray-300">Hva registreres<select className="form-select mt-1 w-full" value={type} onChange={(event) => set("node_type", event.target.value)}>{nodeTypes.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label><p className="rounded-lg bg-green-500/10 px-3 py-2 text-sm text-green-700 dark:text-green-300">{profile.description}</p>
          {profile.parent || form.parent_node_id ? <label className="text-sm font-medium text-gray-600 dark:text-gray-300">Overordnet enhet<select className="form-select mt-1 w-full" value={String(form.parent_node_id ?? "")} onChange={(event) => set("parent_node_id", event.target.value)}><option value="">Direkte på kurs</option>{placements.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label> : null}
          {input("name", "Navn", "text", true)}<div className="grid gap-4 sm:grid-cols-2">{profile.identity ? <>{input("manufacturer", "Merke")}{input("model", "Modell / type")}</> : null}{profile.identity || type === "output" ? input("device_type", type === "output" ? "Utgangstype" : "Enhetstype") : null}{profile.endpoint ? input("endpoint_key", "Utgang / kanal", "text", true) : null}{input("area", "Område")}</div>{input("note", "Teknisk notat")}</> : <>{input("name", "Navn på last", "text", true)}<div className="grid gap-4 sm:grid-cols-2">{input("load_type", "Type")}{input("area", "Område")}</div><label className="text-sm font-medium text-gray-600 dark:text-gray-300">Tilkoblet til<select className="form-select mt-1 w-full" value={String(form.energy_node_id ?? "direct")} onChange={(event) => set("energy_node_id", event.target.value)}><option value="direct">Direkte på kurs</option>{nodeOptions(selectedCircuit.nodes || []).map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label><label className="text-sm font-medium text-gray-600 dark:text-gray-300">Effektprofil<select className="form-select mt-1 w-full" value={String(form.power_profile)} onChange={(event) => set("power_profile", event.target.value)}><option value="unknown">Ikke kjent</option><option value="fixed">Fast effekt</option><option value="variable">Variabel effekt</option></select></label>{form.power_profile === "fixed" ? input("expected_power_w", "Fast effekt (W)", "number", true) : null}{form.power_profile === "variable" ? <div className="grid gap-4 sm:grid-cols-3">{input("min_power_w", "Minimum W", "number")}{input("expected_power_w", "Normal W", "number")}{input("max_power_w", "Maksimum W", "number")}</div> : null}{input("note", "Notat")}</>}
      </section>
      <section className="space-y-4">{state.kind === "node" ? <><div><h3 className="text-sm font-semibold uppercase text-gray-400">HC3-kobling</h3><p className="mt-1 text-xs text-gray-400">{devicesSource || "HC3"} · Søk med navn eller ID i feltene</p></div>{profile.hc3 ? <>{deviceInput("hc3_device_id", "HC3 hovedenhet")}{profile.power !== "none" ? <div className="grid gap-4 sm:grid-cols-2">{deviceInput("hc3_power_device_id", profile.power === "required" ? "HC3 effektmåler (påkrevd)" : "HC3 effektmåler", "power")}{deviceInput("hc3_energy_device_id", "Akkumulert kWh", "energy")}</div> : null}{profile.switch ? deviceInput("hc3_switch_device_id", "HC3 bryterstatus", "switch") : null}{profile.power !== "none" ? <label className="text-sm font-medium text-gray-600 dark:text-gray-300">HC3-samlemåler<select className="form-select mt-1 w-full" disabled={numberOrNull(form.hc3_power_device_id) == null} value={String(form.aggregate_group_key ?? "")} onChange={(event) => set("aggregate_group_key", event.target.value)}><option value="">Ingen samlemåler</option>{data.aggregateMeters.map((meter) => <option value={meter.key} key={meter.key}>{meter.label}</option>)}</select></label> : null}{selectedMain ? <div className="rounded-lg border border-gray-200 p-4 text-sm dark:border-gray-700"><strong className="text-gray-800 dark:text-gray-100">{selectedMain.id} · {selectedMain.name}</strong><p className="mt-1 text-gray-400">{[selectedMain.type, selectedMain.manufacturer, selectedMain.model].filter(Boolean).join(" · ")}</p><p className="mt-1 text-gray-500">{selectedMain.hasPower ? watt(selectedMain.powerW) : "Ingen watt"} · {selectedMain.hasSwitch ? selectedMain.switchState ? "På" : "Av" : "Ingen bryter"}</p></div> : null}</> : <p className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500 dark:bg-gray-700/30">Logiske samlinger har ingen HC3-kobling.</p>}</> : <><h3 className="text-sm font-semibold uppercase text-gray-400">Egenskaper</h3><div className="space-y-3"><Toggle checked={Boolean(form.active)} label="Aktiv" change={(next) => set("active", next)} /><Toggle checked={Boolean(form.controllable)} label="Styrbar" change={(next) => set("controllable", next)} /><Toggle checked={Boolean(form.critical)} label="Kritisk" change={(next) => set("critical", next)} /></div></>}{state.kind === "node" ? <Toggle checked={Boolean(form.active)} label="Aktiv" change={(next) => set("active", next)} /> : null}</section>
    </div>{error ? <p className="mx-6 mb-3 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">{error}</p> : null}<footer className="sticky bottom-0 flex justify-end gap-3 border-t border-gray-100 bg-white px-6 py-4 dark:border-gray-700 dark:bg-gray-800"><button type="button" className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={close}>Avbryt</button><button type="submit" className="btn bg-green-600 text-white hover:bg-green-700" disabled={busy}>{busy ? "Lagrer ..." : editing ? "Lagre" : "Opprett"}</button></footer>
    {([undefined, "power", "energy", "switch"] as const).map((capability) => <datalist id={`hc3-${capability || "all"}`} key={capability || "all"}>{devices.filter((device) => !capability || (capability === "power" ? device.hasPower : capability === "energy" ? device.hasEnergy : device.hasSwitch)).map((device) => <option value={device.id} key={device.id}>{device.id} · {device.name} · {device.type}</option>)}</datalist>)}</form></div>;
}

function LoadRow({ load, measured, circuit, node, canManage, edit }: { load: EnergyLoadItem; measured: boolean; circuit: EnergyCircuit; node?: EnergyNode; canManage: boolean; edit: (state: EditorState) => void }) {
  return <div className={`grid grid-cols-[1fr_auto] items-center gap-4 border-t border-gray-100 py-2.5 pl-7 text-sm dark:border-gray-700/60 ${load.active === false ? "opacity-50" : ""}`}><div><strong className="text-gray-700 dark:text-gray-200">{load.name}</strong><span className="ml-2 text-xs text-gray-400">{[load.loadType, load.area].filter(Boolean).join(" · ") || "Last"}</span>{load.critical ? <span className="ml-2 rounded bg-yellow-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-yellow-700 dark:text-yellow-300">Kritisk</span> : null}{load.controllable ? <span className="ml-2 rounded bg-sky-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-sky-700 dark:text-sky-300">Styrbar</span> : null}</div><div className="flex items-center gap-3 tabular-nums"><span>{loadPower(load, measured)}</span>{canManage ? <button className="text-green-600 hover:underline" onClick={() => edit({ kind: "load", circuit, node, load })}>Rediger</button> : null}</div></div>;
}

function NodeRow({ node, circuit, depth, live, canManage, edit, inheritedMeter = false }: { node: EnergyNode; circuit: EnergyCircuit; depth: number; live: Record<string, EnergyNodeLive>; canManage: boolean; edit: (state: EditorState) => void; inheritedMeter?: boolean }) {
  const current = live[String(node.id)];
  const measured = inheritedMeter || node.hasMeter || node.hc3PowerDeviceId != null;
  const power = current?.currentPowerW ?? node.currentPowerW;
  const switchState = current?.switchState ?? node.switchState;
  return <div className={`border-l-2 ${measured ? "border-green-500/50" : "border-gray-200 dark:border-gray-700"}`} style={{ marginLeft: `${Math.min(depth, 4) * 18}px` }}><div className="grid grid-cols-[1fr_auto] items-center gap-4 py-3 pl-4"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><strong className="text-gray-800 dark:text-gray-100">{node.name}</strong><span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-gray-500 dark:bg-gray-700">{nodeTypes.find((item) => item.value === node.nodeType)?.label || node.nodeType}</span>{node.aggregateMeter ? <span className="rounded bg-sky-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-sky-700 dark:text-sky-300">{node.aggregateMeter.label}</span> : null}{node.topologyWarning ? <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-red-600">{node.topologyWarning}</span> : null}</div><div className="mt-1 truncate text-xs text-gray-400">{[node.manufacturer, node.model, node.deviceType, node.endpointKey ? `kanal ${node.endpointKey}` : null, node.area, node.hc3DeviceId || node.hc3PowerDeviceId ? `HC3 ${node.hc3DeviceId || node.hc3PowerDeviceId}` : null].filter(Boolean).join(" · ") || "Uten tekniske detaljer"}</div></div><div className="flex flex-wrap items-center justify-end gap-3 text-sm tabular-nums"><strong>{watt(power)}</strong>{node.hasSwitch ? <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${switchState ? "bg-green-500/15 text-green-600 dark:text-green-400" : "bg-gray-100 text-gray-500 dark:bg-gray-700"}`}>{switchState ? "PÅ" : "AV"}</span> : null}{current?.error ? <span className="text-xs text-red-500" title={current.error}>Feil</span> : null}{canManage ? <><button className="text-green-600 hover:underline" onClick={() => edit({ kind: "node", circuit, node })}>Rediger</button><button className="text-green-600 hover:underline" onClick={() => edit({ kind: "node", circuit, parent: node })}>+ Enhet</button><button className="text-green-600 hover:underline" onClick={() => edit({ kind: "load", circuit, parent: node })}>+ Last</button></> : null}</div></div>{node.loads.map((load) => <LoadRow load={load} measured={measured} circuit={circuit} node={node} canManage={canManage} edit={edit} key={load.id} />)}{node.children.map((child) => <NodeRow node={child} circuit={circuit} depth={depth + 1} live={live} canManage={canManage} edit={edit} inheritedMeter={measured} key={child.id} />)}</div>;
}

export function EnergyCircuitLoads({ data, reload }: { data: EnergyCircuitLoadsData; reload: () => void }) {
  const [filter, setFilter] = useState<"without" | "sunbeds" | "all">("without");
  const [mapping, setMapping] = useState<MappingFilter>("all");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(data.circuits.filter((circuit) => circuit.loadCount || circuit.nodeCount).map((circuit) => circuit.key)));
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [live, setLive] = useState<Record<string, EnergyNodeLive>>({});
  const [aggregateLive, setAggregateLive] = useState<Record<string, EnergyAggregateLive>>({});
  const [checkedAt, setCheckedAt] = useState<string | null>(null);
  const [liveError, setLiveError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [devices, setDevices] = useState<Hc3EnergyDevice[]>([]);
  const [devicesSource, setDevicesSource] = useState("");
  const [devicesError, setDevicesError] = useState("");
  const [loadingDevices, setLoadingDevices] = useState(false);

  const refreshLive = useCallback(async () => {
    setRefreshing(true);
    try { const result = await domainApi.get<EnergyNodesLiveResponse>("/api/energy/nodes/live"); setLive(result.nodes || {}); setAggregateLive(result.aggregateMeters || {}); setCheckedAt(result.checkedAt || null); setLiveError(result.configured ? "" : "HC3-tilgang er ikke konfigurert"); }
    catch (reason) { setLiveError(reason instanceof Error ? reason.message : "Kunne ikke lese HC3"); }
    finally { setRefreshing(false); }
  }, []);

  const ensureDevices = useCallback(async () => {
    if (devices.length || loadingDevices || !data.canManage) return;
    setLoadingDevices(true); setDevicesError("");
    try { const result = await domainApi.get<Hc3EnergyDevicesResponse>("/api/energy/hc3-devices"); setDevices(result.devices || []); setDevicesSource(result.source || "HC3"); setDevicesError(result.error || ""); }
    catch (reason) { setDevicesError(reason instanceof Error ? reason.message : "Kunne ikke hente HC3-enheter"); }
    finally { setLoadingDevices(false); }
  }, [data.canManage, devices.length, loadingDevices]);

  useEffect(() => { void refreshLive(); const refreshVisible = () => { if (document.visibilityState === "visible") void refreshLive(); }; const timer = window.setInterval(refreshVisible, 15_000); document.addEventListener("visibilitychange", refreshVisible); return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", refreshVisible); }; }, [refreshLive]);
  const openEditor = (state: EditorState) => { setEditor(state); if (state.kind === "node") void ensureDevices(); setExpanded((current) => new Set(current).add(state.circuit.key)); };
  const normalized = query.trim().toLocaleLowerCase("nb-NO");
  const circuits = useMemo(() => data.circuits.filter((circuit) => {
    if (filter !== "all" && circuit.isSunbed !== (filter === "sunbeds")) return false;
    if (mapping === "mapped" && !(circuit.activeLoadCount > 0 && circuit.unmeasuredLoadCount === 0)) return false;
    if (mapping === "needs-work" && !(circuit.activeLoadCount > 0 && circuit.unmeasuredLoadCount > 0)) return false;
    if (mapping === "empty" && !(circuit.loadCount === 0 && circuit.nodeCount === 0)) return false;
    if (!normalized) return true;
    const nodes = flattenNodes(circuit.nodes);
    const text = `${circuit.circuitNo} ${circuit.description} ${nodes.map((node) => `${node.name} ${node.manufacturer} ${node.model} ${node.area}`).join(" ")} ${[...circuit.directLoads, ...nodes.flatMap((node) => node.loads)].map((load) => `${load.name} ${load.loadType} ${load.area}`).join(" ")}`;
    return text.toLocaleLowerCase("nb-NO").includes(normalized);
  }), [data.circuits, filter, mapping, normalized]);
  const toggle = (key: string) => setExpanded((current) => { const next = new Set(current); next.has(key) ? next.delete(key) : next.add(key); return next; });
  const saveAndReload = () => { reload(); void refreshLive(); };

  return <div className="space-y-5"><Panel title="Sanntid og kartlegging" subtitle={liveError || `HC3 lest ${checkedTime(checkedAt)}`} actions={<button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={refreshing} onClick={() => void refreshLive()}><MosaicIcon name="refresh" className={refreshing ? "animate-spin" : ""} />Oppdater nå</button>}><div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-5">{data.aggregateMeters.map((meter) => { const current = aggregateLive[meter.key]; return <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-700/30" key={meter.key}><span className="text-xs font-semibold uppercase text-gray-400">{meter.label}</span><strong className="mt-1 block text-lg tabular-nums text-gray-800 dark:text-gray-100">{watt(current?.currentPowerW)}</strong><small className="text-gray-400">{kwh(current?.currentEnergyKwh)} · R{meter.realtimeId}/A{meter.accumulatedId} · {meter.mappedNodeCount || 0}/{meter.memberPowerIds?.length || 0} koblet</small></div>; })}</div></Panel>
    <Panel><div className="flex flex-wrap items-center gap-3 p-5"><input className="form-input min-w-64 flex-1" placeholder="Søk etter kurs, enhet eller last" value={query} onChange={(event) => setQuery(event.target.value)} /><select className="form-select" value={filter} onChange={(event) => setFilter(event.target.value as typeof filter)}><option value="without">Uten solsenger</option><option value="sunbeds">Kun solsenger</option><option value="all">Alle kurser</option></select><select className="form-select" value={mapping} onChange={(event) => setMapping(event.target.value as MappingFilter)}><option value="all">Alle statuser</option><option value="mapped">Kartlagt</option><option value="needs-work">Mangler måling</option><option value="empty">Ikke kartlagt</option></select><span className="text-sm text-gray-400">{circuits.length} vist</span><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setExpanded(new Set())}>Lukk alle</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setExpanded(new Set(circuits.map((circuit) => circuit.key)))}>Åpne alle</button></div></Panel>
    {circuits.map((circuit) => { const coverage = circuit.activeLoadCount ? Math.round((circuit.measuredLoadCount / circuit.activeLoadCount) * 100) : 0; const currentPower = circuitPower(circuit, live); return <Panel title={`Kurs ${circuit.circuitNo ?? "-"} · ${circuit.description || "Uten navn"}`} subtitle={`${circuit.breaker || "Ukjent vern"} · ${circuit.measurementDetail || circuit.measurementMode}`} actions={<div className="flex flex-wrap items-center justify-end gap-3"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${coverage === 100 ? "bg-green-500/15 text-green-600 dark:text-green-400" : coverage > 0 ? "bg-yellow-500/15 text-yellow-700 dark:text-yellow-300" : "bg-gray-100 text-gray-500 dark:bg-gray-700"}`}>{circuit.measurementMode} · {coverage}%</span><strong className="tabular-nums">{watt(currentPower)} <span className="font-normal text-gray-400">/ {watt(circuit.expectedPowerW)}</span></strong>{data.canManage ? <><button className="text-sm font-medium text-green-600" onClick={() => openEditor({ kind: "node", circuit })}>+ Enhet</button><button className="text-sm font-medium text-green-600" onClick={() => openEditor({ kind: "load", circuit })}>+ Last</button></> : null}<button className="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-700" onClick={() => toggle(circuit.key)} title={expanded.has(circuit.key) ? "Lukk" : "Åpne"}><MosaicIcon name={expanded.has(circuit.key) ? "chevron-up" : "chevron-down"} /></button></div>} key={circuit.key}>{expanded.has(circuit.key) ? <div className="px-5 py-2"><div className="mb-2 flex flex-wrap gap-4 text-xs text-gray-400"><span>{circuit.activeLoadCount} aktive laster</span><span>{circuit.nodeCount} enheter</span><span>{circuit.measuredLoadCount} målt</span><span>{circuit.unmeasuredLoadCount} mangler måling</span>{circuit.note ? <span>{circuit.note}</span> : null}</div>{circuit.directLoads.map((load) => <LoadRow load={load} measured={Boolean(load.measuredDirect || load.fibaroMeterId)} circuit={circuit} canManage={Boolean(data.canManage)} edit={openEditor} key={load.id} />)}{circuit.nodes.map((node) => <NodeRow node={node} circuit={circuit} depth={0} live={live} canManage={Boolean(data.canManage)} edit={openEditor} key={node.id} />)}{!circuit.directLoads.length && !circuit.nodes.length ? <p className="py-6 text-center text-sm text-gray-400">Ingen enheter eller laster er lagt inn</p> : null}</div> : null}</Panel>; })}
    {!circuits.length ? <Panel><p className="p-8 text-center text-sm text-gray-400">Ingen kurser passer med filtrene.</p></Panel> : null}{devicesError ? <p className="rounded-lg bg-yellow-500/10 px-4 py-3 text-sm text-yellow-700 dark:text-yellow-300">{devicesError}</p> : null}{editor ? <EnergyEditor state={editor} data={data} devices={devices} devicesSource={loadingDevices ? "Henter HC3-enheter ..." : devicesSource} close={() => setEditor(null)} saved={saveAndReload} /> : null}</div>;
}
