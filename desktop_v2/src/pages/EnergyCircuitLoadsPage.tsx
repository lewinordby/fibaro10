import {
  ApiOutlined,
  ApartmentOutlined,
  BranchesOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  CheckCircleOutlined,
  EditOutlined,
  GatewayOutlined,
  LinkOutlined,
  PlusOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { App as AntApp, Button, Checkbox, Empty, Form, Input, InputNumber, Modal, Select, Switch, Tooltip } from "antd";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
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
  expectedPowerW?: number | null;
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

const nodeTypes = [
  { value: "zwave_device", label: "Z-Wave-enhet" },
  { value: "output", label: "Utgang / kanal" },
  { value: "child_device", label: "Underordnet enhet" },
  { value: "meter", label: "Frittstående målepunkt" },
  { value: "logical", label: "Logisk tilkoblingspunkt" },
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
  const label = `${device.id} · ${device.name || "Uten navn"}${capabilities ? ` · ${capabilities}` : ""}`;
  return {
    value: device.id,
    label,
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
        {[device.type, device.powerW != null ? wattText(device.powerW) : null, device.hasSwitch ? (device.switchState ? "På" : "Av") : null]
          .filter(Boolean)
          .join(" · ")}
      </small>
    </div>
  );
}

function LoadLine({
  load,
  onEdit,
}: {
  load: EnergyCircuitLoadItem;
  onEdit: (load: EnergyCircuitLoadItem) => void;
}) {
  return (
    <div className={`energy-topology-load ${load.active === false ? "inactive" : ""}`}>
      <span className="energy-topology-load-mark" />
      <div>
        <strong>{load.name}</strong>
        <small>{[load.loadType, load.area].filter(Boolean).join(" · ") || "Last"}</small>
      </div>
      <span>{wattText(load.expectedPowerW)}</span>
      {load.controllable ? <StatusTag tone="info">Styrbar</StatusTag> : <span />}
      <Tooltip title="Rediger last">
        <button type="button" className="energy-icon-action" aria-label={`Rediger ${load.name}`} onClick={() => onEdit(load)}>
          <EditOutlined />
        </button>
      </Tooltip>
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
}: {
  node: EnergyConnectionNode;
  live: Record<string, EnergyNodeLive>;
  depth: number;
  onEditNode: (node: EnergyConnectionNode) => void;
  onAddChild: (node: EnergyConnectionNode) => void;
  onAddLoad: (node: EnergyConnectionNode) => void;
  onEditLoad: (node: EnergyConnectionNode, load: EnergyCircuitLoadItem) => void;
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
        <div className="energy-topology-node-actions">
          <Tooltip title="Ny last på denne enheten">
            <button type="button" className="energy-icon-action" aria-label="Ny last" onClick={() => onAddLoad(node)}><PlusOutlined /></button>
          </Tooltip>
          <Tooltip title="Ny utgang eller underenhet">
            <button type="button" className="energy-icon-action" aria-label="Ny underenhet" onClick={() => onAddChild(node)}><BranchesOutlined /></button>
          </Tooltip>
          <Tooltip title="Rediger enhet">
            <button type="button" className="energy-icon-action" aria-label="Rediger enhet" onClick={() => onEditNode(node)}><EditOutlined /></button>
          </Tooltip>
        </div>
      </div>
      {current?.error ? <div className="energy-topology-live-error">{current.error}</div> : null}
      {node.topologyWarning ? <div className="energy-topology-live-error">{node.topologyWarning}</div> : null}
      {node.loads.length ? (
        <div className="energy-topology-load-list">
          {node.loads.map((load) => <LoadLine key={load.id} load={load} onEdit={(item) => onEditLoad(node, item)} />)}
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
        <div className="energy-course-card-actions">
          <Button size="small" icon={<PlusOutlined />} onClick={onAddDirectLoad}>Last direkte</Button>
          <Button size="small" type="primary" icon={<GatewayOutlined />} onClick={onAddNode}>Ny enhet</Button>
        </div>
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
              {circuit.directLoads.map((load) => <LoadLine key={load.id} load={load} onEdit={(item) => onEditLoad(null, item)} />)}
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
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [nodeEditor, setNodeEditor] = useState<NodeEditorState | null>(null);
  const [loadEditor, setLoadEditor] = useState<LoadEditorState | null>(null);
  const [saving, setSaving] = useState(false);
  const [live, setLive] = useState<Record<string, EnergyNodeLive>>({});
  const [liveCheckedAt, setLiveCheckedAt] = useState<string | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [devices, setDevices] = useState<Hc3EnergyDevice[]>([]);
  const [devicesSource, setDevicesSource] = useState<string | null>(null);
  const [devicesError, setDevicesError] = useState<string | null>(null);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const circuitLoads = data.energyCircuitLoads;
  const circuits = circuitLoads?.circuits ?? [];
  const visibleCircuits = circuits.filter((circuit) => filter === "all" || circuit.isSunbed === (filter === "sunbeds"));
  const selectedNodeCircuitNo = Form.useWatch("circuitNo", nodeForm);
  const selectedLoadCircuitNo = Form.useWatch("circuitNo", loadForm);
  const selectedMainDeviceId = Form.useWatch("hc3DeviceId", nodeForm);
  const selectedPowerDeviceId = Form.useWatch("hc3PowerDeviceId", nodeForm);
  const selectedSwitchDeviceId = Form.useWatch("hc3SwitchDeviceId", nodeForm);

  const allNodes = useMemo(() => circuits.flatMap((circuit) => flattenNodes(circuit.nodes)), [circuits]);
  const nodeById = useMemo(() => new Map(allNodes.map((node) => [node.id, node])), [allNodes]);
  const devicesById = useMemo(() => new Map(devices.map((device) => [device.id, device])), [devices]);
  const deviceOptions = useMemo(() => devices.map(hc3Option), [devices]);
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
    () => flattenNodes(selectedNodeCircuit?.nodes ?? []).filter((node) => node.id !== nodeEditor?.node?.id).map((node) => ({
      value: node.id,
      label: `${node.name}${node.endpointKey ? ` · ${node.endpointKey}` : ""}`,
    })),
    [nodeEditor?.node?.id, selectedNodeCircuit],
  );
  const selectedLoadNodeOptions = useMemo(
    () => [
      { value: "direct" as const, label: "Direkte på kurs" },
      ...flattenNodes(selectedLoadCircuit?.nodes ?? []).map((node) => ({ value: node.id, label: node.name })),
    ],
    [selectedLoadCircuit],
  );

  const refreshLive = useCallback(async () => {
    try {
      const result = await fetchEnergyNodesLive();
      setLive(result.nodes ?? {});
      setLiveCheckedAt(result.checkedAt || null);
      setLiveError(result.configured ? null : "HC3-tilgang er ikke konfigurert");
    } catch (error) {
      setLiveError(error instanceof Error ? error.message : "Kunne ikke lese HC3 akkurat nå");
    }
  }, []);

  useEffect(() => {
    void refreshLive();
    const timer = window.setInterval(() => void refreshLive(), 10_000);
    return () => window.clearInterval(timer);
  }, [refreshLive]);

  useEffect(() => {
    if (expanded.size || !circuits.length) return;
    setExpanded(new Set(circuits.filter((circuit) => circuit.loadCount > 0 || circuit.nodeCount > 0).map((circuit) => circuit.key)));
  }, [circuits, expanded.size]);

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
      expectedPowerW: load?.expectedPowerW ?? undefined,
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
    const nodeId = values.energyNodeId === "direct" ? null : cleanNumber(values.energyNodeId as number | null);
    const payload: EnergyLoadCreateInput = {
      name: cleanText(values.name) ?? "",
      load_type: cleanText(values.loadType),
      area: cleanText(values.area),
      circuit_no: cleanNumber(values.circuitNo),
      expected_power_w: cleanNumber(values.expectedPowerW),
      energy_node_id: nodeId,
      measured_direct: false,
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

  const activeNodes = circuitLoads.summary.nodes ?? allNodes.length;
  const measuredPercent = circuitLoads.summary.activeLoads
    ? Math.round((circuitLoads.summary.measuredLoadCount / circuitLoads.summary.activeLoads) * 100)
    : 0;

  return (
    <div className="page-stack energy-topology-page">
      <section className="work-card energy-topology-toolbar">
        <div>
          <span className="energy-circuit-eyebrow">Energi</span>
          <h2>Kurs, enheter og laster</h2>
          <p>Elektrisk struktur med direkte laster, Z-Wave-enheter, utganger, underenheter og levende HC3-verdier.</p>
        </div>
        <div className="energy-topology-toolbar-actions">
          <span className={liveError ? "energy-live-state warn" : "energy-live-state ok"}>
            {liveError ? liveError : `HC3 lest ${checkedTime(liveCheckedAt)}`}
          </span>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => void refreshLive()}>Oppdater nå</Button>
        </div>
      </section>

      <section className="energy-topology-summary" aria-label="Oppsummering">
        <div><span>Kurser</span><strong>{visibleCircuits.length}</strong><small>{circuits.length} totalt</small></div>
        <div><span>Enheter/utganger</span><strong>{activeNodes}</strong><small>registrerte punkter</small></div>
        <div><span>Aktive laster</span><strong>{circuitLoads.summary.activeLoads}</strong><small>{circuitLoads.summary.loads} totalt</small></div>
        <div><span>Måledekning</span><strong>{measuredPercent}%</strong><small>{circuitLoads.summary.unmeteredLoadCount} uten dekning</small></div>
        <div><span>Teoretisk effekt</span><strong>{wattText(circuitLoads.summary.expectedPowerW)}</strong><small>aktive laster</small></div>
      </section>

      <section className="work-card energy-topology-board">
        <div className="energy-topology-board-head">
          <div className="energy-circuit-filter" role="group" aria-label="Filtrer kursliste">
            {circuitFilters.map((item) => (
              <button type="button" key={item.key} className={filter === item.key ? "active" : ""} onClick={() => setFilter(item.key)}>{item.label}</button>
            ))}
          </div>
          <div className="energy-topology-board-actions">
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
            />
          ))}
        </div>
      </section>

      <Modal
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
                <Form.Item name="circuitNo" label="Kurs" rules={[{ required: true, message: "Velg kurs" }]}>
                  <Select
                    options={circuitOptions}
                    showSearch
                    optionFilterProp="label"
                    disabled={nodeEditor?.mode === "edit"}
                  />
                </Form.Item>
                <Form.Item name="parentNodeId" label="Overordnet enhet">
                  <Select allowClear options={selectedNodeOptions} placeholder="Direkte på kurs" showSearch optionFilterProp="label" />
                </Form.Item>
              </div>
              <div className="energy-form-two">
                <Form.Item name="nodeType" label="Hva slags punkt" rules={[{ required: true, message: "Velg type" }]}>
                  <Select options={nodeTypes} />
                </Form.Item>
                <Form.Item name="endpointKey" label="Utgang / kanal">
                  <Input placeholder="For eksempel 1, Q1 eller 123.1" />
                </Form.Item>
              </div>
              <Form.Item name="name" label="Navn" rules={[{ required: true, message: "Navn må fylles ut" }]}>
                <Input autoFocus placeholder="For eksempel Fibaro Double Switch loft" />
              </Form.Item>
              <div className="energy-form-two">
                <Form.Item name="manufacturer" label="Merke">
                  <Input placeholder="Fibaro, Aeotec, Qubino ..." />
                </Form.Item>
                <Form.Item name="model" label="Modell / typebetegnelse">
                  <Input placeholder="FGS-223, Smart Switch 7 ..." />
                </Form.Item>
              </div>
              <div className="energy-form-two">
                <Form.Item name="deviceType" label="Enhetstype">
                  <Input placeholder="HC3-type eller teknisk betegnelse" />
                </Form.Item>
                <Form.Item name="area" label="Område">
                  <Input placeholder="Loft, 1.etg, VIP ..." />
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
                  options={deviceOptions}
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
                  options={deviceOptions}
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
              <div className="energy-form-switches">
                <Form.Item name="hasMeter" label="Har måling" valuePropName="checked"><Switch /></Form.Item>
                <Form.Item name="hasSwitch" label="Har bryter" valuePropName="checked"><Switch /></Form.Item>
                <Form.Item name="active" label="Aktiv" valuePropName="checked"><Switch /></Form.Item>
              </div>
              <div className="energy-form-help">
                <CheckCircleOutlined />
                <span>Effekt leses fra valgt effektmåler. Av/på leses fra valgt bryter. De kan være samme HC3-enhet eller ulike underenheter.</span>
              </div>
            </section>
          </div>
        </Form>
      </Modal>

      <Modal
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
              <Select options={circuitOptions} showSearch optionFilterProp="label" />
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
              <Input placeholder="Lys, vifte, varme ..." />
            </Form.Item>
            <Form.Item name="area" label="Område">
              <Input placeholder="Loft, VIP ..." />
            </Form.Item>
            <Form.Item name="expectedPowerW" label="Teoretisk effekt">
              <InputNumber min={0} precision={0} addonAfter="W" className="edit-number" />
            </Form.Item>
          </div>
          <div className="energy-form-checkboxes">
            <Form.Item name="active" valuePropName="checked"><Checkbox>Aktiv</Checkbox></Form.Item>
            <Form.Item name="controllable" valuePropName="checked"><Checkbox>Styrbar</Checkbox></Form.Item>
            <Form.Item name="critical" valuePropName="checked"><Checkbox>Kritisk</Checkbox></Form.Item>
          </div>
          <Form.Item name="note" label="Notat">
            <Input.TextArea rows={3} placeholder="Kort beskrivelse av lasten eller koblingen" />
          </Form.Item>
          <div className="energy-form-help">
            <LinkOutlined />
            <span>HC3-ID og sanntidsmåling registreres på enheten eller utgangen over lasten. Da kan samme måler dekke flere laster uten dobbeltelling.</span>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
