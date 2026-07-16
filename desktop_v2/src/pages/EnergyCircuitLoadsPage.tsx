import {
  ApiOutlined,
  ApartmentOutlined,
  BranchesOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  EditOutlined,
  GatewayOutlined,
  LinkOutlined,
  PlusOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { App as AntApp, Button, Checkbox, Empty, Form, Input, InputNumber, Modal, Segmented, Select, Switch, Tooltip } from "antd";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  createEnergyLoad,
  createEnergyNode,
  fetchEnergyNodesLive,
  fetchHc3EnergyDevices,
  updateEnergyLoad,
  updateEnergyNode,
  type EnergyCircuitLoadCircuit,
  type EnergyCircuitLoadItem,
  type EnergyConnectionNode,
  type EnergyLoadCreateInput,
  type EnergyNodeInput,
  type EnergyNodeLive,
  type Hc3EnergyDevice,
  type ModuleResponse,
} from "../api";
import { decimal } from "../format";
import "../styles/energy.css";

type CircuitFilter = "without-sunbeds" | "all" | "sunbeds";
type CircuitMappingFilter = "all" | "mapped" | "needs-work" | "empty";

type NodeFormValues = {
  circuitNo?: number | null;
  parentNodeId?: number | null;
  nodeType?: string;
  name?: string;
  area?: string;
  endpointKey?: string;
  manufacturer?: string;
  model?: string;
  deviceType?: string;
  hc3DeviceId?: number | null;
  hc3PowerDeviceId?: number | null;
  hc3SwitchDeviceId?: number | null;
  hasMeter?: boolean;
  hasSwitch?: boolean;
  active?: boolean;
  note?: string;
};

type LoadFormValues = {
  circuitNo?: number | null;
  energyNodeId?: number | "direct" | null;
  name?: string;
  loadType?: string;
  area?: string;
  powerProfile?: "unknown" | "fixed" | "variable";
  expectedPowerW?: number | null;
  minPowerW?: number | null;
  maxPowerW?: number | null;
  controllable?: boolean;
  critical?: boolean;
  active?: boolean;
  note?: string;
};

type NodeEditorState = {
  mode: "create" | "edit";
  circuit: EnergyCircuitLoadCircuit;
  node?: EnergyConnectionNode | null;
  parent?: EnergyConnectionNode | null;
};

type LoadEditorState = {
  mode: "create" | "edit";
  circuit: EnergyCircuitLoadCircuit;
  node?: EnergyConnectionNode | null;
  load?: EnergyCircuitLoadItem | null;
};

const circuitFilters: Array<{ key: CircuitFilter; label: string }> = [
  { key: "without-sunbeds", label: "Uten solsenger" },
  { key: "all", label: "Alle kurser" },
  { key: "sunbeds", label: "Kun solsenger" },
];

const mappingFilters: Array<{ key: CircuitMappingFilter; label: string }> = [
  { key: "all", label: "Alle statuser" },
  { key: "mapped", label: "Kartlagt" },
  { key: "needs-work", label: "Mangler måling" },
  { key: "empty", label: "Ikke kartlagt" },
];

const nodeTypes = [
  { value: "zwave_device", label: "Z-Wave-enhet" },
  { value: "output", label: "Utgang" },
  { value: "child_device", label: "Underenhet" },
  { value: "meter", label: "Målepunkt" },
  { value: "logical", label: "Logisk punkt" },
];

const loadTypeSuggestions = ["Avfukter", "Belysning", "Elektronikk", "Kremautomat", "Lading", "Motor", "Solseng", "Varmepumpe", "Varme", "Ventilasjon"]
  .map((value) => ({ value }));

const powerProfiles = [
  { value: "unknown", label: "Ikke kjent" },
  { value: "fixed", label: "Fast effekt" },
  { value: "variable", label: "Variabel effekt" },
];

function cleanText(value?: string | null): string | null {
  const text = String(value ?? "").trim();
  return text || null;
}

function cleanNumber(value?: number | null): number | null {
  return value == null || Number.isNaN(Number(value)) ? null : Number(value);
}

function wattText(value?: number | null): string {
  if (value == null || Number.isNaN(Number(value))) return "–";
  return `${decimal(Number(value), 0)} W`;
}

function loadPowerText(load: EnergyCircuitLoadItem): string {
  if (load.powerProfile === "variable") {
    if (load.minPowerW != null && load.maxPowerW != null) {
      return `${decimal(Number(load.minPowerW), 0)}–${decimal(Number(load.maxPowerW), 0)} W`;
    }
    if (load.minPowerW != null) return `Fra ${decimal(Number(load.minPowerW), 0)} W`;
    if (load.maxPowerW != null) return `Inntil ${decimal(Number(load.maxPowerW), 0)} W`;
    if (load.expectedPowerW != null) return wattText(load.expectedPowerW);
    return "–";
  }
  return wattText(load.expectedPowerW);
}

function loadPowerDetail(load: EnergyCircuitLoadItem): string {
  if (load.powerProfile === "variable") {
    return load.expectedPowerW != null ? `${wattText(load.expectedPowerW)} normalt` : "Variabel effekt";
  }
  if (load.powerProfile === "fixed" || load.expectedPowerW != null) return "Fast effekt";
  return "Effekt ikke registrert";
}

function circuitNoText(value?: number | null): string {
  return value == null ? "?" : String(value).padStart(2, "0");
}

function checkedTime(value?: string | null): string {
  if (!value) return "ikke lest";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function flattenNodes(nodes: EnergyConnectionNode[]): EnergyConnectionNode[] {
  return nodes.flatMap((node) => [node, ...flattenNodes(node.children ?? [])]);
}

function nodePlacementOptions(
  nodes: EnergyConnectionNode[],
  depth = 0,
  excludedIds: ReadonlySet<number> = new Set(),
): Array<{ value: number; label: string }> {
  return nodes.flatMap((node) => excludedIds.has(node.id) ? [] : [
    { value: node.id, label: `${"— ".repeat(depth)}${node.name} · ${nodeTypeLabel(node.nodeType)}` },
    ...nodePlacementOptions(node.children ?? [], depth + 1, excludedIds),
  ]);
}

function branchPower(node: EnergyConnectionNode, live: Record<string, EnergyNodeLive>): number | null {
  const own = live[String(node.id)]?.currentPowerW;
  if (own != null && Number.isFinite(Number(own))) return Number(own);
  const childValues = (node.children ?? []).map((child) => branchPower(child, live)).filter((value): value is number => value != null);
  return childValues.length ? childValues.reduce((sum, value) => sum + value, 0) : null;
}

function circuitLivePower(circuit: EnergyCircuitLoadCircuit, live: Record<string, EnergyNodeLive>): number | null {
  const values = circuit.nodes.map((node) => branchPower(node, live)).filter((value): value is number => value != null);
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

function coveragePercent(circuit: EnergyCircuitLoadCircuit): number {
  return circuit.activeLoadCount ? Math.round((circuit.measuredLoadCount / circuit.activeLoadCount) * 100) : 0;
}

function circuitMatchesMapping(circuit: EnergyCircuitLoadCircuit, filter: CircuitMappingFilter): boolean {
  if (filter === "mapped") return circuit.activeLoadCount > 0 && circuit.unmeasuredLoadCount === 0;
  if (filter === "needs-work") return circuit.activeLoadCount > 0 && circuit.unmeasuredLoadCount > 0;
  if (filter === "empty") return circuit.loadCount === 0 && circuit.nodeCount === 0;
  return true;
}

function nodeTypeLabel(nodeType?: string | null): string {
  return nodeTypes.find((item) => item.value === nodeType)?.label ?? "Tilkoblingspunkt";
}

function nodeIcon(node: EnergyConnectionNode): ReactNode {
  if (node.nodeType === "output") return <BranchesOutlined />;
  if (node.nodeType === "meter") return <ThunderboltOutlined />;
  if (node.nodeType === "child_device") return <ApartmentOutlined />;
  if (node.nodeType === "logical") return <LinkOutlined />;
  return <GatewayOutlined />;
}

function StatusTag({ tone = "default", children }: { tone?: string; children: ReactNode }) {
  return <span className={`energy-tag ${tone}`}>{children}</span>;
}

function hc3Option(device: Hc3EnergyDevice) {
  const capabilities = [device.hasPower ? "effekt" : null, device.hasSwitch ? "bryter" : null].filter(Boolean).join(" + ");
  const unavailable = device.dead === true || device.enabled === false;
  const label = `${device.id} · ${device.name || "Uten navn"}${capabilities ? ` · ${capabilities}` : ""}${unavailable ? " · utilgjengelig" : ""}`;
  return {
    value: device.id,
    label,
    disabled: unavailable,
    search: `${device.id} ${device.name || ""} ${device.type || ""} ${device.manufacturer || ""} ${device.model || ""}`.toLowerCase(),
  };
}

function Hc3DeviceFact({ label, device }: { label: string; device?: Hc3EnergyDevice | null }) {
  if (!device) return null;
  return (
    <div className="energy-hc3-device-fact">
      <span>{label}</span>
      <strong>{device.id} · {device.name || "Uten navn"}</strong>
      <small>
        {[
          device.type,
          device.powerW != null ? wattText(device.powerW) : null,
          device.hasSwitch ? (device.switchState ? "På" : "Av") : null,
          device.dead ? "Ikke tilgjengelig" : device.enabled === false ? "Deaktivert" : "Klar",
        ]
          .filter(Boolean)
          .join(" · ")}
      </small>
    </div>
  );
}

function LoadLine({
  load,
  onEdit,
  canManage,
}: {
  load: EnergyCircuitLoadItem;
  onEdit: (load: EnergyCircuitLoadItem) => void;
  canManage: boolean;
}) {
  return (
    <div className={`energy-topology-load ${load.active === false ? "inactive" : ""}`}>
      <span className="energy-topology-load-mark" />
      <div>
        <strong>{load.name}</strong>
        <small>{[load.loadType, load.area, loadPowerDetail(load)].filter(Boolean).join(" · ") || "Last"}</small>
      </div>
      <span>{loadPowerText(load)}</span>
      <span className="energy-topology-load-tags">
        {load.active === false ? <StatusTag>Inaktiv</StatusTag> : null}
        {load.critical ? <StatusTag tone="warn">Kritisk</StatusTag> : null}
        {load.controllable ? <StatusTag tone="info">Styrbar</StatusTag> : null}
      </span>
      {canManage ? (
        <Tooltip title="Rediger last">
          <button type="button" className="energy-icon-action" aria-label={`Rediger ${load.name}`} onClick={() => onEdit(load)}>
            <EditOutlined />
          </button>
        </Tooltip>
      ) : <span aria-hidden="true" />}
    </div>
  );
}

function NodeTree({
  node,
  live,
  depth,
  onEditNode,
  onAddChild,
  onAddLoad,
  onEditLoad,
  canManage,
}: {
  node: EnergyConnectionNode;
  live: Record<string, EnergyNodeLive>;
  depth: number;
  onEditNode: (node: EnergyConnectionNode) => void;
  onAddChild: (node: EnergyConnectionNode) => void;
  onAddLoad: (node: EnergyConnectionNode) => void;
  onEditLoad: (node: EnergyConnectionNode, load: EnergyCircuitLoadItem) => void;
  canManage: boolean;
}) {
  const current = live[String(node.id)];
  const power = current?.currentPowerW;
  const switchState = current?.switchState;
  const status = current?.status ?? node.liveStatus ?? "pending";
  const meta = [node.manufacturer, node.model, node.endpointKey ? `kanal ${node.endpointKey}` : null].filter(Boolean).join(" · ");
  const ids = [
    node.hc3DeviceId ? `enhet ${node.hc3DeviceId}` : null,
    node.hc3PowerDeviceId ? `effekt ${node.hc3PowerDeviceId}` : null,
    node.hc3SwitchDeviceId ? `bryter ${node.hc3SwitchDeviceId}` : null,
  ].filter(Boolean).join(" · ");
  return (
    <div className={`energy-topology-node depth-${Math.min(depth, 3)} ${node.active ? "" : "inactive"}`}>
      <div className="energy-topology-node-head">
        <span className="energy-topology-node-icon">{nodeIcon(node)}</span>
        <div className="energy-topology-node-title">
          <div>
            <strong>{node.name}</strong>
            <StatusTag tone={node.hasMeter ? "ok" : "default"}>{nodeTypeLabel(node.nodeType)}</StatusTag>
            {node.hasMeter ? <StatusTag tone="energy">Måler</StatusTag> : null}
            {node.hasSwitch ? <StatusTag tone="info">Bryter</StatusTag> : null}
          </div>
          <small>{meta || node.area || "Ingen merke- eller modelldata"}</small>
          <small>{ids || "HC3-ID er ikke koblet"}</small>
        </div>
        <div className="energy-topology-node-live">
          <strong>{wattText(power)}</strong>
          <span>
            {node.hasSwitch ? (
              <StatusTag tone={switchState === true ? "ok" : switchState === false ? "default" : "warn"}>
                <PoweroffOutlined /> {switchState === true ? "På" : switchState === false ? "Av" : "Ukjent"}
              </StatusTag>
            ) : null}
            <StatusTag tone={status === "ok" ? "ok" : status === "unconfigured" ? "default" : "warn"}>
              {status === "ok" ? "Live" : status === "unconfigured" ? "Ikke koblet" : status === "pending" ? "Venter" : "Sjekk"}
            </StatusTag>
          </span>
          <small>{current?.checkedAt ? `lest ${checkedTime(current.checkedAt)}` : wattText(node.expectedPowerW) + " teori"}</small>
        </div>
        {canManage ? (
          <div className="energy-topology-node-actions">
            <Tooltip title="Legg til last på denne enheten">
              <button type="button" className="energy-icon-action" aria-label="Ny last" onClick={() => onAddLoad(node)}><PlusOutlined /></button>
            </Tooltip>
            <Tooltip title="Legg til utgang eller underenhet">
              <button type="button" className="energy-icon-action" aria-label="Ny underenhet" onClick={() => onAddChild(node)}><BranchesOutlined /></button>
            </Tooltip>
            <Tooltip title="Rediger enhet">
              <button type="button" className="energy-icon-action" aria-label="Rediger enhet" onClick={() => onEditNode(node)}><EditOutlined /></button>
            </Tooltip>
          </div>
        ) : null}
      </div>
      {current?.error ? <div className="energy-topology-live-error">{current.error}</div> : null}
      {node.topologyWarning ? <div className="energy-topology-live-error">{node.topologyWarning}</div> : null}
      {node.loads.length ? (
        <div className="energy-topology-load-list">
          {node.loads.map((load) => <LoadLine key={load.id} load={load} canManage={canManage} onEdit={(item) => onEditLoad(node, item)} />)}
        </div>
      ) : null}
      {node.children.length ? (
        <div className="energy-topology-children">
          {node.children.map((child) => (
            <NodeTree
              key={child.id}
              node={child}
              live={live}
              depth={depth + 1}
              onEditNode={onEditNode}
              onAddChild={onAddChild}
              onAddLoad={onAddLoad}
              onEditLoad={onEditLoad}
              canManage={canManage}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function CourseCard({
  circuit,
  live,
  expanded,
  onToggle,
  onAddNode,
  onAddDirectLoad,
  onEditNode,
  onAddChild,
  onAddLoad,
  onEditLoad,
  canManage,
}: {
  circuit: EnergyCircuitLoadCircuit;
  live: Record<string, EnergyNodeLive>;
  expanded: boolean;
  onToggle: () => void;
  onAddNode: () => void;
  onAddDirectLoad: () => void;
  onEditNode: (node: EnergyConnectionNode) => void;
  onAddChild: (node: EnergyConnectionNode) => void;
  onAddLoad: (node: EnergyConnectionNode) => void;
  onEditLoad: (node: EnergyConnectionNode | null, load: EnergyCircuitLoadItem) => void;
  canManage: boolean;
}) {
  const livePower = circuitLivePower(circuit, live);
  const coverage = coveragePercent(circuit);
  const hasContent = circuit.nodes.length > 0 || circuit.directLoads.length > 0;
  return (
    <article className={`energy-course-card ${hasContent ? "has-content" : "empty"}`}>
      <header className="energy-course-card-head">
        <button type="button" className="energy-course-expand" onClick={onToggle} aria-label={expanded ? "Skjul kursdetaljer" : "Vis kursdetaljer"}>
          {expanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
        </button>
        <div className="energy-course-number">{circuitNoText(circuit.circuitNo)}</div>
        <div className="energy-course-title">
          <strong>{circuit.description || "Uten kursnavn"}</strong>
          <span>{[circuit.breaker, circuit.breakerType, circuit.status].filter(Boolean).join(" · ") || "Tekniske kursdata mangler"}</span>
        </div>
        <div className="energy-course-tags">
          {circuit.isSunbed ? <StatusTag tone="sun">Solseng</StatusTag> : null}
          <StatusTag tone={coverage === 100 ? "ok" : coverage > 0 ? "partial" : "warn"}>{circuit.measurementMode}</StatusTag>
          <span>{circuit.nodeCount} enheter · {circuit.activeLoadCount} laster</span>
        </div>
        <div className="energy-course-power">
          <span>Effekt nå</span>
          <strong>{wattText(livePower)}</strong>
          <small>{wattText(circuit.expectedPowerW)} registrert</small>
        </div>
        {canManage ? (
          <div className="energy-course-card-actions">
            <Button size="small" icon={<PlusOutlined />} onClick={onAddDirectLoad}>Direkte last</Button>
            <Button size="small" type="primary" icon={<GatewayOutlined />} onClick={onAddNode}>Legg til enhet</Button>
          </div>
        ) : null}
      </header>
      {expanded ? (
        <div className="energy-course-card-body">
          <div className="energy-course-coverage">
            <span style={{ width: `${coverage}%` }} />
            <small>{circuit.measurementDetail}</small>
          </div>
          {circuit.directLoads.length ? (
            <section className="energy-direct-loads">
              <div className="energy-topology-section-label"><ApiOutlined /> Direkte på kurs</div>
              {circuit.directLoads.map((load) => <LoadLine key={load.id} load={load} canManage={canManage} onEdit={(item) => onEditLoad(null, item)} />)}
            </section>
          ) : null}
          {circuit.nodes.length ? (
            <section className="energy-node-tree">
              <div className="energy-topology-section-label"><GatewayOutlined /> Enheter og utganger</div>
              {circuit.nodes.map((node) => (
                <NodeTree
                  key={node.id}
                  node={node}
                  live={live}
                  depth={0}
                  onEditNode={onEditNode}
                  onAddChild={onAddChild}
                  onAddLoad={onAddLoad}
                  onEditLoad={(selectedNode, load) => onEditLoad(selectedNode, load)}
                  canManage={canManage}
                />
              ))}
            </section>
          ) : null}
          {!hasContent ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen enheter eller laster er registrert på kurset" /> : null}
        </div>
      ) : null}
    </article>
  );
}

export default function EnergyCircuitLoadsPage({ data, onReload }: { data: ModuleResponse; onReload: () => Promise<unknown> | unknown }) {
  const { message } = AntApp.useApp();
  const [nodeForm] = Form.useForm<NodeFormValues>();
  const [loadForm] = Form.useForm<LoadFormValues>();
  const [filter, setFilter] = useState<CircuitFilter>("without-sunbeds");
  const [mappingFilter, setMappingFilter] = useState<CircuitMappingFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [nodeEditor, setNodeEditor] = useState<NodeEditorState | null>(null);
  const [loadEditor, setLoadEditor] = useState<LoadEditorState | null>(null);
  const [saving, setSaving] = useState(false);
  const [liveRefreshing, setLiveRefreshing] = useState(false);
  const [live, setLive] = useState<Record<string, EnergyNodeLive>>({});
  const [liveCheckedAt, setLiveCheckedAt] = useState<string | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [devices, setDevices] = useState<Hc3EnergyDevice[]>([]);
  const [devicesSource, setDevicesSource] = useState<string | null>(null);
  const [devicesError, setDevicesError] = useState<string | null>(null);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const initializedExpansion = useRef(false);
  const circuitLoads = data.energyCircuitLoads;
  const circuits = circuitLoads?.circuits ?? [];
  const canManage = Boolean(circuitLoads?.canManage);
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const visibleCircuits = useMemo(() => circuits.filter((circuit) => {
    if (filter !== "all" && circuit.isSunbed !== (filter === "sunbeds")) return false;
    if (!circuitMatchesMapping(circuit, mappingFilter)) return false;
    if (!normalizedSearch) return true;
    const nodeText = flattenNodes(circuit.nodes).map((node) => `${node.name} ${node.manufacturer || ""} ${node.model || ""} ${node.area || ""}`).join(" ");
    const loadText = [...circuit.directLoads, ...flattenNodes(circuit.nodes).flatMap((node) => node.loads)]
      .map((load) => `${load.name} ${load.loadType || ""} ${load.area || ""}`)
      .join(" ");
    return `${circuit.circuitNo ?? ""} ${circuit.description || ""} ${nodeText} ${loadText}`.toLowerCase().includes(normalizedSearch);
  }), [circuits, filter, mappingFilter, normalizedSearch]);
  const visibleSummary = useMemo(() => visibleCircuits.reduce((summary, circuit) => ({
    nodes: summary.nodes + circuit.nodeCount,
    loads: summary.loads + circuit.loadCount,
    activeLoads: summary.activeLoads + circuit.activeLoadCount,
    measuredLoads: summary.measuredLoads + circuit.measuredLoadCount,
    unmeasuredLoads: summary.unmeasuredLoads + circuit.unmeasuredLoadCount,
    expectedPowerW: summary.expectedPowerW + Number(circuit.expectedPowerW || 0),
  }), { nodes: 0, loads: 0, activeLoads: 0, measuredLoads: 0, unmeasuredLoads: 0, expectedPowerW: 0 }), [visibleCircuits]);
  const selectedNodeCircuitNo = Form.useWatch("circuitNo", nodeForm);
  const selectedLoadCircuitNo = Form.useWatch("circuitNo", loadForm);
  const selectedMainDeviceId = Form.useWatch("hc3DeviceId", nodeForm);
  const selectedPowerDeviceId = Form.useWatch("hc3PowerDeviceId", nodeForm);
  const selectedSwitchDeviceId = Form.useWatch("hc3SwitchDeviceId", nodeForm);
  const selectedPowerProfile = Form.useWatch("powerProfile", loadForm) ?? "unknown";

  const allNodes = useMemo(() => circuits.flatMap((circuit) => flattenNodes(circuit.nodes)), [circuits]);
  const devicesById = useMemo(() => new Map(devices.map((device) => [device.id, device])), [devices]);
  const deviceOptions = useMemo(() => devices.map(hc3Option), [devices]);
  const powerDeviceOptions = useMemo(
    () => devices.filter((device) => device.hasPower || device.id === Number(selectedPowerDeviceId)).map(hc3Option),
    [devices, selectedPowerDeviceId],
  );
  const switchDeviceOptions = useMemo(
    () => devices.filter((device) => device.hasSwitch || device.id === Number(selectedSwitchDeviceId)).map(hc3Option),
    [devices, selectedSwitchDeviceId],
  );
  const areaSuggestions = useMemo(() => Array.from(new Set([
    ...allNodes.map((node) => node.area),
    ...circuits.flatMap((circuit) => [...circuit.directLoads, ...flattenNodes(circuit.nodes).flatMap((node) => node.loads)]).map((load) => load.area),
  ].filter((value): value is string => Boolean(value)))).sort().map((value) => ({ value })), [allNodes, circuits]);
  const manufacturerSuggestions = useMemo(() => Array.from(new Set(devices.map((device) => device.manufacturer).filter((value): value is string => Boolean(value)))).sort().map((value) => ({ value })), [devices]);
  const modelSuggestions = useMemo(() => Array.from(new Set(devices.map((device) => device.model).filter((value): value is string => Boolean(value)))).sort().map((value) => ({ value })), [devices]);
  const circuitOptions = useMemo(
    () => circuits.filter((circuit) => circuit.circuitNo != null).map((circuit) => ({
      value: Number(circuit.circuitNo),
      label: `K${circuitNoText(circuit.circuitNo)} · ${circuit.description || "Uten kursnavn"}`,
    })),
    [circuits],
  );
  const selectedNodeCircuit = circuits.find((circuit) => circuit.circuitNo === selectedNodeCircuitNo) ?? nodeEditor?.circuit ?? null;
  const selectedLoadCircuit = circuits.find((circuit) => circuit.circuitNo === selectedLoadCircuitNo) ?? loadEditor?.circuit ?? null;
  const selectedNodeOptions = useMemo(
    () => {
      const excludedIds = new Set(nodeEditor?.node ? flattenNodes([nodeEditor.node]).map((node) => node.id) : []);
      return nodePlacementOptions(selectedNodeCircuit?.nodes ?? [], 0, excludedIds);
    },
    [nodeEditor?.node, selectedNodeCircuit],
  );
  const selectedLoadNodeOptions = useMemo(
    () => [
      { value: "direct" as const, label: "Direkte på kurs" },
      ...nodePlacementOptions(selectedLoadCircuit?.nodes ?? []),
    ],
    [selectedLoadCircuit],
  );

  const refreshLive = useCallback(async () => {
    setLiveRefreshing(true);
    try {
      const result = await fetchEnergyNodesLive();
      setLive(result.nodes ?? {});
      setLiveCheckedAt(result.checkedAt || null);
      setLiveError(result.configured ? null : "HC3-tilgang er ikke konfigurert");
    } catch (error) {
      setLiveError(error instanceof Error ? error.message : "Kunne ikke lese HC3 akkurat nå");
    } finally {
      setLiveRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refreshLive();
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void refreshLive();
    };
    const timer = window.setInterval(refreshWhenVisible, 15_000);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [refreshLive]);

  useEffect(() => {
    if (initializedExpansion.current || !circuits.length) return;
    initializedExpansion.current = true;
    setExpanded(new Set(circuits.filter((circuit) => circuit.loadCount > 0 || circuit.nodeCount > 0).map((circuit) => circuit.key)));
  }, [circuits]);

  if (!circuitLoads) return null;

  async function ensureDevices() {
    if (devices.length || loadingDevices) return;
    setLoadingDevices(true);
    try {
      const result = await fetchHc3EnergyDevices();
      setDevices(result.devices ?? []);
      setDevicesSource(result.source);
      setDevicesError(result.error ?? null);
    } catch (error) {
      setDevicesError(error instanceof Error ? error.message : "Kunne ikke hente HC3-enheter");
    } finally {
      setLoadingDevices(false);
    }
  }

  function toggleCircuit(key: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function openNodeEditor(circuit: EnergyCircuitLoadCircuit, node?: EnergyConnectionNode | null, parent?: EnergyConnectionNode | null) {
    void ensureDevices();
    nodeForm.resetFields();
    nodeForm.setFieldsValue({
      circuitNo: circuit.circuitNo ?? null,
      parentNodeId: node?.parentNodeId ?? parent?.id ?? null,
      nodeType: node?.nodeType ?? (parent ? "output" : "zwave_device"),
      name: node?.name ?? "",
      area: node?.area ?? undefined,
      endpointKey: node?.endpointKey ?? undefined,
      manufacturer: node?.manufacturer ?? undefined,
      model: node?.model ?? undefined,
      deviceType: node?.deviceType ?? undefined,
      hc3DeviceId: node?.hc3DeviceId ?? undefined,
      hc3PowerDeviceId: node?.hc3PowerDeviceId ?? undefined,
      hc3SwitchDeviceId: node?.hc3SwitchDeviceId ?? undefined,
      hasMeter: node?.hasMeter ?? false,
      hasSwitch: node?.hasSwitch ?? false,
      active: node?.active ?? true,
      note: node?.note ?? undefined,
    });
    setNodeEditor({ mode: node ? "edit" : "create", circuit, node, parent });
    setExpanded((current) => new Set(current).add(circuit.key));
  }

  function openLoadEditor(circuit: EnergyCircuitLoadCircuit, node?: EnergyConnectionNode | null, load?: EnergyCircuitLoadItem | null) {
    loadForm.resetFields();
    loadForm.setFieldsValue({
      circuitNo: circuit.circuitNo ?? null,
      energyNodeId: load?.energyNodeId ?? node?.id ?? "direct",
      name: load?.name ?? "",
      loadType: load?.loadType ?? undefined,
      area: load?.area ?? node?.area ?? undefined,
      powerProfile: (load?.powerProfile as LoadFormValues["powerProfile"]) ?? (load?.expectedPowerW != null ? "fixed" : "unknown"),
      expectedPowerW: load?.expectedPowerW ?? undefined,
      minPowerW: load?.minPowerW ?? undefined,
      maxPowerW: load?.maxPowerW ?? undefined,
      controllable: Boolean(load?.controllable),
      critical: Boolean(load?.critical),
      active: load?.active !== false,
      note: load?.note ?? undefined,
    });
    setLoadEditor({ mode: load ? "edit" : "create", circuit, node, load });
    setExpanded((current) => new Set(current).add(circuit.key));
  }

  function applyMainDevice(deviceId?: number | null) {
    if (deviceId == null) return;
    const device = devicesById.get(deviceId);
    if (!device) return;
    const current = nodeForm.getFieldsValue();
    nodeForm.setFieldsValue({
      name: cleanText(current.name) ? current.name : device.name ?? "",
      manufacturer: cleanText(current.manufacturer) ? current.manufacturer : device.manufacturer ?? undefined,
      model: cleanText(current.model) ? current.model : device.model ?? undefined,
      deviceType: cleanText(current.deviceType) ? current.deviceType : device.type ?? undefined,
      hc3PowerDeviceId: current.hc3PowerDeviceId ?? (device.hasPower ? device.id : undefined),
      hc3SwitchDeviceId: current.hc3SwitchDeviceId ?? (device.hasSwitch ? device.id : undefined),
      hasMeter: Boolean(current.hasMeter || device.hasPower),
      hasSwitch: Boolean(current.hasSwitch || device.hasSwitch),
    });
  }

  async function saveNode() {
    if (!nodeEditor || saving) return;
    const values = await nodeForm.validateFields();
    const payload: EnergyNodeInput = {
      name: cleanText(values.name) ?? "",
      circuit_no: Number(values.circuitNo),
      parent_node_id: cleanNumber(values.parentNodeId),
      node_type: cleanText(values.nodeType),
      manufacturer: cleanText(values.manufacturer),
      model: cleanText(values.model),
      device_type: cleanText(values.deviceType),
      hc3_device_id: cleanNumber(values.hc3DeviceId),
      hc3_power_device_id: cleanNumber(values.hc3PowerDeviceId),
      hc3_switch_device_id: cleanNumber(values.hc3SwitchDeviceId),
      endpoint_key: cleanText(values.endpointKey),
      has_meter: Boolean(values.hasMeter),
      has_switch: Boolean(values.hasSwitch),
      area: cleanText(values.area),
      active: values.active !== false,
      note: cleanText(values.note),
    };
    setSaving(true);
    try {
      const result = nodeEditor.mode === "edit" && nodeEditor.node
        ? await updateEnergyNode(nodeEditor.node.id, payload)
        : await createEnergyNode(payload);
      message.success(String(result.message || "Enheten er lagret"));
      await onReload();
      await refreshLive();
      setNodeEditor(null);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Kunne ikke lagre enheten");
    } finally {
      setSaving(false);
    }
  }

  async function saveLoad() {
    if (!loadEditor || saving) return;
    const values = await loadForm.validateFields();
    if (values.powerProfile === "fixed" && values.expectedPowerW == null) {
      message.error("Fyll inn effekt for en fast last.");
      return;
    }
    if (values.powerProfile === "variable" && values.minPowerW == null && values.expectedPowerW == null && values.maxPowerW == null) {
      message.error("Fyll inn minst én effektverdi for en variabel last.");
      return;
    }
    if (values.minPowerW != null && values.maxPowerW != null && values.minPowerW > values.maxPowerW) {
      message.error("Minimum effekt kan ikke være høyere enn maksimum effekt.");
      return;
    }
    if (values.expectedPowerW != null && values.minPowerW != null && values.expectedPowerW < values.minPowerW) {
      message.error("Normal effekt kan ikke være lavere enn minimum effekt.");
      return;
    }
    if (values.expectedPowerW != null && values.maxPowerW != null && values.expectedPowerW > values.maxPowerW) {
      message.error("Normal effekt kan ikke være høyere enn maksimum effekt.");
      return;
    }
    const nodeId = values.energyNodeId === "direct" ? null : cleanNumber(values.energyNodeId as number | null);
    const powerProfile = values.powerProfile ?? "unknown";
    const payload: EnergyLoadCreateInput = {
      name: cleanText(values.name) ?? "",
      load_type: cleanText(values.loadType),
      area: cleanText(values.area),
      circuit_no: cleanNumber(values.circuitNo),
      power_profile: powerProfile,
      expected_power_w: powerProfile === "unknown" ? null : cleanNumber(values.expectedPowerW),
      min_power_w: powerProfile === "variable" ? cleanNumber(values.minPowerW) : null,
      max_power_w: powerProfile === "variable" ? cleanNumber(values.maxPowerW) : null,
      energy_node_id: nodeId,
      measured_direct: false,
      fibaro_device_id: null,
      fibaro_meter_id: null,
      zwave_switch_id: null,
      controllable: Boolean(values.controllable),
      critical: Boolean(values.critical),
      active: values.active !== false,
      note: cleanText(values.note),
    };
    setSaving(true);
    try {
      const result = loadEditor.mode === "edit" && loadEditor.load
        ? await updateEnergyLoad(loadEditor.load.id, payload)
        : await createEnergyLoad(payload);
      message.success(String(result.message || "Lasten er lagret"));
      await onReload();
      setLoadEditor(null);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Kunne ikke lagre lasten");
    } finally {
      setSaving(false);
    }
  }

  const measuredPercent = visibleSummary.activeLoads
    ? Math.round((visibleSummary.measuredLoads / visibleSummary.activeLoads) * 100)
    : 0;

  return (
    <div className="page-stack energy-topology-page">
      <datalist id="energy-area-suggestions">
        {areaSuggestions.map((item) => <option key={item.value} value={item.value} />)}
      </datalist>
      <datalist id="energy-manufacturer-suggestions">
        {manufacturerSuggestions.map((item) => <option key={item.value} value={item.value} />)}
      </datalist>
      <datalist id="energy-model-suggestions">
        {modelSuggestions.map((item) => <option key={item.value} value={item.value} />)}
      </datalist>
      <datalist id="energy-load-type-suggestions">
        {loadTypeSuggestions.map((item) => <option key={item.value} value={item.value} />)}
      </datalist>
      <section className="work-card energy-topology-toolbar">
        <div>
          <span className="energy-circuit-eyebrow">Energi</span>
          <h2>Kurs, enheter og laster</h2>
        </div>
        <div className="energy-topology-toolbar-actions">
          {!canManage ? <span className="energy-live-state">Lesevisning</span> : null}
          <span className={liveError ? "energy-live-state warn" : "energy-live-state ok"}>
            {liveError ? liveError : `HC3 lest ${checkedTime(liveCheckedAt)}`}
          </span>
          <Button size="small" icon={<ReloadOutlined />} loading={liveRefreshing} onClick={() => void refreshLive()}>Oppdater nå</Button>
        </div>
      </section>

      <section className="energy-topology-summary" aria-label="Oppsummering">
        <div><span>Kurser</span><strong>{visibleCircuits.length}</strong><small>{circuits.length} totalt</small></div>
        <div><span>Enheter/utganger</span><strong>{visibleSummary.nodes}</strong><small>i viste kurser</small></div>
        <div><span>Aktive laster</span><strong>{visibleSummary.activeLoads}</strong><small>{visibleSummary.loads} registrert</small></div>
        <div><span>Måledekning</span><strong>{measuredPercent}%</strong><small>{visibleSummary.unmeasuredLoads} uten dekning</small></div>
        <div><span>Teoretisk effekt</span><strong>{wattText(visibleSummary.expectedPowerW)}</strong><small>i viste kurser</small></div>
      </section>

      <section className="work-card energy-topology-board">
        <div className="energy-topology-board-head">
          <div className="energy-topology-board-controls">
            <Input
              allowClear
              className="energy-topology-search"
              prefix={<SearchOutlined />}
              placeholder="Søk etter kurs, enhet eller last"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            <div className="energy-circuit-filter" role="group" aria-label="Filtrer kursliste">
              {circuitFilters.map((item) => (
                <button type="button" key={item.key} className={filter === item.key ? "active" : ""} onClick={() => setFilter(item.key)}>{item.label}</button>
              ))}
            </div>
            <Select
              aria-label="Kartleggingsstatus"
              className="energy-mapping-filter"
              value={mappingFilter}
              options={mappingFilters.map((item) => ({ value: item.key, label: item.label }))}
              onChange={(value) => setMappingFilter(value)}
            />
          </div>
          <div className="energy-topology-board-actions">
            <span>{visibleCircuits.length} vist</span>
            <Button size="small" onClick={() => setExpanded(new Set())}>Lukk alle</Button>
            <Button size="small" onClick={() => setExpanded(new Set(visibleCircuits.map((circuit) => circuit.key)))}>Åpne alle</Button>
          </div>
        </div>
        <div className="energy-course-card-list">
          {visibleCircuits.map((circuit) => (
            <CourseCard
              key={circuit.key}
              circuit={circuit}
              live={live}
              expanded={expanded.has(circuit.key)}
              onToggle={() => toggleCircuit(circuit.key)}
              onAddNode={() => openNodeEditor(circuit)}
              onAddDirectLoad={() => openLoadEditor(circuit)}
              onEditNode={(node) => openNodeEditor(circuit, node)}
              onAddChild={(node) => openNodeEditor(circuit, null, node)}
              onAddLoad={(node) => openLoadEditor(circuit, node)}
              onEditLoad={(node, load) => openLoadEditor(circuit, node, load)}
              canManage={canManage}
            />
          ))}
          {!visibleCircuits.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen kurser passer med filtrene" /> : null}
        </div>
      </section>

      <Modal
        centered
        rootClassName="energy-topology-modal"
        title={nodeEditor?.mode === "edit" ? "Rediger enhet eller utgang" : nodeEditor?.parent ? "Ny utgang eller underenhet" : "Ny enhet på kurs"}
        open={Boolean(nodeEditor)}
        width={980}
        confirmLoading={saving}
        okText={nodeEditor?.mode === "edit" ? "Lagre" : "Opprett"}
        onOk={() => void saveNode()}
        onCancel={() => setNodeEditor(null)}
        destroyOnHidden
      >
        <Form form={nodeForm} layout="vertical" className="energy-node-form">
          <div className="energy-form-context">
            <GatewayOutlined />
            <span>
              <strong>{nodeEditor?.circuit.description || "Kurs"}</strong>
              <small>{nodeEditor?.parent ? `Opprettes under ${nodeEditor.parent.name}` : "Knytt fysisk enhet, måler og eventuelle utganger til kurset."}</small>
            </span>
          </div>
          <div className="energy-node-form-grid">
            <section>
              <h4>Plassering og identitet</h4>
              <div className="energy-form-two">
                <Form.Item
                  name="circuitNo"
                  label="Kurs"
                  extra={nodeEditor?.mode === "edit" ? "Ved flytting følger underenheter og tilknyttede laster med." : undefined}
                  rules={[{ required: true, message: "Velg kurs" }]}
                >
                  <Select
                    options={circuitOptions}
                    showSearch
                    optionFilterProp="label"
                    onChange={() => nodeForm.setFieldValue("parentNodeId", null)}
                  />
                </Form.Item>
                <Form.Item name="parentNodeId" label="Overordnet enhet">
                  <Select allowClear options={selectedNodeOptions} placeholder="Direkte på kurs" showSearch optionFilterProp="label" />
                </Form.Item>
              </div>
              <Form.Item name="nodeType" label="Hva registreres" rules={[{ required: true, message: "Velg type" }]}>
                <Segmented block options={nodeTypes} />
              </Form.Item>
              <Form.Item name="name" label="Navn" rules={[{ required: true, message: "Navn må fylles ut" }]}>
                <Input autoFocus placeholder="For eksempel Fibaro Double Switch loft" />
              </Form.Item>
              <div className="energy-form-two">
                <Form.Item name="manufacturer" label="Merke">
                  <Input list="energy-manufacturer-suggestions" placeholder="Fibaro, Aeotec, Qubino ..." />
                </Form.Item>
                <Form.Item name="model" label="Modell / typebetegnelse">
                  <Input list="energy-model-suggestions" placeholder="FGS-223, Smart Switch 7 ..." />
                </Form.Item>
              </div>
              <div className="energy-form-three">
                <Form.Item name="deviceType" label="Enhetstype">
                  <Input placeholder="HC3-type eller teknisk betegnelse" />
                </Form.Item>
                <Form.Item name="area" label="Område">
                  <Input list="energy-area-suggestions" placeholder="Loft, 1.etg, VIP ..." />
                </Form.Item>
                <Form.Item name="endpointKey" label="Utgang / kanal">
                  <Input placeholder="1, Q1 eller 123.1" />
                </Form.Item>
              </div>
              <Form.Item name="note" label="Teknisk notat">
                <Input.TextArea rows={3} placeholder="Kobling, plassering eller annet som er nyttig senere" />
              </Form.Item>
            </section>

            <section>
              <div className="energy-form-section-title">
                <h4>HC3-kobling</h4>
                <small>{loadingDevices ? "Henter enheter ..." : devicesSource || "HC3"}</small>
              </div>
              {devicesError ? <div className="energy-form-warning">{devicesError}</div> : null}
              <Form.Item name="hc3DeviceId" label="HC3 hovedenhet">
                <Select
                  allowClear
                  showSearch
                  loading={loadingDevices}
                  options={deviceOptions}
                  optionFilterProp="search"
                  placeholder="Søk på ID, navn, merke eller type"
                  onChange={(value) => applyMainDevice(value)}
                />
              </Form.Item>
              <Form.Item name="hc3PowerDeviceId" label="HC3 effektmåler">
                <Select
                  allowClear
                  showSearch
                  loading={loadingDevices}
                  options={powerDeviceOptions}
                  optionFilterProp="search"
                  placeholder="Enheten som gir W akkurat nå"
                  onChange={(value) => nodeForm.setFieldValue("hasMeter", value != null)}
                />
              </Form.Item>
              <Form.Item name="hc3SwitchDeviceId" label="HC3 bryter">
                <Select
                  allowClear
                  showSearch
                  loading={loadingDevices}
                  options={switchDeviceOptions}
                  optionFilterProp="search"
                  placeholder="Enheten som gir av/på-status"
                  onChange={(value) => nodeForm.setFieldValue("hasSwitch", value != null)}
                />
              </Form.Item>
              <div className="energy-hc3-selected">
                <Hc3DeviceFact label="Hovedenhet" device={devicesById.get(Number(selectedMainDeviceId))} />
                <Hc3DeviceFact label="Effekt" device={devicesById.get(Number(selectedPowerDeviceId))} />
                <Hc3DeviceFact label="Bryter" device={devicesById.get(Number(selectedSwitchDeviceId))} />
              </div>
              {!selectedMainDeviceId && !selectedPowerDeviceId && !selectedSwitchDeviceId ? (
                <div className="energy-form-warning">Ingen HC3-enhet er valgt. Punktet lagres uten levende verdier.</div>
              ) : null}
              {selectedPowerDeviceId && !devicesById.get(Number(selectedPowerDeviceId))?.hasPower ? (
                <div className="energy-form-warning">Valgt effekt-ID rapporterer ikke sanntidseffekt i HC3-inventaret.</div>
              ) : null}
              {selectedSwitchDeviceId && !devicesById.get(Number(selectedSwitchDeviceId))?.hasSwitch ? (
                <div className="energy-form-warning">Valgt bryter-ID rapporterer ikke av/på-status i HC3-inventaret.</div>
              ) : null}
              <div className="energy-form-switches">
                <Form.Item name="active" label="Aktiv" valuePropName="checked"><Switch /></Form.Item>
              </div>
              <Form.Item name="hasMeter" hidden valuePropName="checked"><Checkbox /></Form.Item>
              <Form.Item name="hasSwitch" hidden valuePropName="checked"><Checkbox /></Form.Item>
            </section>
          </div>
        </Form>
      </Modal>

      <Modal
        centered
        rootClassName="energy-topology-modal"
        title={loadEditor?.mode === "edit" ? "Rediger last" : "Ny last"}
        open={Boolean(loadEditor)}
        width={760}
        confirmLoading={saving}
        okText={loadEditor?.mode === "edit" ? "Lagre" : "Opprett"}
        onOk={() => void saveLoad()}
        onCancel={() => setLoadEditor(null)}
        destroyOnHidden
      >
        <Form form={loadForm} layout="vertical" className="energy-load-form">
          <div className="energy-form-context">
            <ThunderboltOutlined />
            <span>
              <strong>{loadEditor?.circuit.description || "Kurs"}</strong>
              <small>Lasten kan ligge direkte på kurset eller under en registrert enhet eller utgang.</small>
            </span>
          </div>
          <div className="energy-form-two">
            <Form.Item name="circuitNo" label="Kurs" rules={[{ required: true, message: "Velg kurs" }]}>
              <Select
                options={circuitOptions}
                showSearch
                optionFilterProp="label"
                onChange={() => loadForm.setFieldValue("energyNodeId", "direct")}
              />
            </Form.Item>
            <Form.Item name="energyNodeId" label="Tilkoblet til" rules={[{ required: true, message: "Velg plassering" }]}>
              <Select options={selectedLoadNodeOptions} showSearch optionFilterProp="label" />
            </Form.Item>
          </div>
          <Form.Item name="name" label="Navn på last" rules={[{ required: true, message: "Navn må fylles ut" }]}>
            <Input autoFocus placeholder="For eksempel avtrekksvifte tak" />
          </Form.Item>
          <div className="energy-form-three">
            <Form.Item name="loadType" label="Type">
              <Input list="energy-load-type-suggestions" placeholder="Lys, vifte, varme ..." />
            </Form.Item>
            <Form.Item name="area" label="Område">
              <Input list="energy-area-suggestions" placeholder="Loft, VIP ..." />
            </Form.Item>
            <Form.Item name="powerProfile" label="Effektprofil">
              <Select options={powerProfiles} />
            </Form.Item>
          </div>
          {selectedPowerProfile === "fixed" ? (
            <div className="energy-power-fields fixed">
              <Form.Item name="expectedPowerW" label="Fast effekt" rules={[{ required: true, message: "Fyll inn effekt" }]}>
                <InputNumber min={0} precision={0} addonAfter="W" className="edit-number" />
              </Form.Item>
            </div>
          ) : null}
          {selectedPowerProfile === "variable" ? (
            <div className="energy-power-fields variable">
              <Form.Item name="minPowerW" label="Minimum">
                <InputNumber min={0} precision={0} addonAfter="W" className="edit-number" />
              </Form.Item>
              <Form.Item name="expectedPowerW" label="Normal effekt">
                <InputNumber min={0} precision={0} addonAfter="W" className="edit-number" />
              </Form.Item>
              <Form.Item name="maxPowerW" label="Maksimum">
                <InputNumber min={0} precision={0} addonAfter="W" className="edit-number" />
              </Form.Item>
            </div>
          ) : null}
          {selectedPowerProfile === "unknown" ? (
            <div className="energy-form-neutral">Effekt ikke registrert.</div>
          ) : null}
          <div className="energy-form-checkboxes">
            <Form.Item name="active" valuePropName="checked"><Checkbox>Aktiv</Checkbox></Form.Item>
            <Form.Item name="controllable" valuePropName="checked"><Checkbox>Styrbar</Checkbox></Form.Item>
            <Form.Item name="critical" valuePropName="checked"><Checkbox>Kritisk</Checkbox></Form.Item>
          </div>
          <Form.Item name="note" label="Notat">
            <Input.TextArea rows={3} placeholder="Kort beskrivelse av lasten eller koblingen" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
