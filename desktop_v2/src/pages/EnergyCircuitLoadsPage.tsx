import { App as AntApp, Button, Checkbox, Form, Input, InputNumber, Modal, Select } from "antd";
import { useMemo, useState, type ReactNode } from "react";
import {
  createEnergyLoad,
  updateEnergyLoad,
  type EnergyCircuitLoadCircuit,
  type EnergyCircuitLoadItem,
  type EnergyCircuitMeterGroup,
  type EnergyLoadCreateInput,
  type EnergyLoadUpdateInput,
  type ModuleResponse,
} from "../api";
import { decimal } from "../format";
import "../styles/energy.css";

type CircuitFilter = "without-sunbeds" | "all" | "sunbeds";
type MeterMode = "existing" | "new" | "direct" | "unmetered";

type AddLoadFormValues = {
  circuitNo?: number | null;
  meterMode?: MeterMode;
  existingMeterId?: number | null;
  newMeterId?: number | null;
  name?: string;
  loadType?: string;
  area?: string;
  expectedPowerW?: number | null;
  fibaroDeviceId?: number | null;
  zwaveSwitchId?: number | null;
  controllable?: boolean;
  critical?: boolean;
  active?: boolean;
  note?: string;
};

type AddLoadState = {
  mode: "create" | "edit";
  circuit?: EnergyCircuitLoadCircuit | null;
  group?: EnergyCircuitMeterGroup | null;
  load?: EnergyCircuitLoadItem | null;
};

const circuitFilters: Array<{ key: CircuitFilter; label: string }> = [
  { key: "without-sunbeds", label: "Uten solsenger" },
  { key: "all", label: "Alle kurser" },
  { key: "sunbeds", label: "Kun solsenger" },
];

function wattText(value?: number | null): string {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return `${decimal(Number(value), 0)} W`;
}

function cleanText(value?: string | null): string | null {
  const trimmed = String(value ?? "").trim();
  return trimmed || null;
}

function cleanNumber(value?: number | null): number | null {
  if (value == null || Number.isNaN(Number(value))) return null;
  return Number(value);
}

function meterLabel(group: EnergyCircuitMeterGroup): string {
  if (group.type === "circuit_meter") return "Kursmåler";
  if (group.type === "shared_meter") return "Undermåler";
  if (group.type === "direct_meter") return group.meterId ? "Lastmåler" : "Direkte";
  return "På kurs";
}

function meterTone(group: EnergyCircuitMeterGroup): string {
  if (group.type === "circuit_meter") return "ok";
  if (group.type === "shared_meter") return "info";
  if (group.type === "direct_meter") return "energy";
  return "warn";
}

function meterOptionsForCircuit(circuit?: EnergyCircuitLoadCircuit | null) {
  const options = new Map<number, { label: string; value: number }>();
  for (const group of circuit?.measurementGroups ?? []) {
    if (group.meterId == null) continue;
    options.set(Number(group.meterId), {
      value: Number(group.meterId),
      label: `${group.meterId} - ${group.label}`,
    });
  }
  return Array.from(options.values()).sort((left, right) => left.value - right.value);
}

function meterUsage(circuits: EnergyCircuitLoadCircuit[]) {
  const usage = new Map<number, Array<{ circuit: EnergyCircuitLoadCircuit; group: EnergyCircuitMeterGroup }>>();
  for (const circuit of circuits) {
    for (const group of circuit.measurementGroups) {
      if (group.meterId == null) continue;
      const meterId = Number(group.meterId);
      usage.set(meterId, [...(usage.get(meterId) ?? []), { circuit, group }]);
    }
  }
  return usage;
}

function defaultMeterMode(circuit?: EnergyCircuitLoadCircuit | null, group?: EnergyCircuitMeterGroup | null): MeterMode {
  if (group?.meterId != null) return "existing";
  if (group?.type === "direct_meter") return "direct";
  if (group?.type === "unmetered") return "unmetered";
  return meterOptionsForCircuit(circuit).length ? "existing" : "new";
}

function meterModeForLoad(circuit: EnergyCircuitLoadCircuit | null | undefined, load: EnergyCircuitLoadItem): MeterMode {
  if (load.fibaroMeterId != null) {
    return meterOptionsForCircuit(circuit).some((option) => option.value === Number(load.fibaroMeterId)) ? "existing" : "new";
  }
  return load.measuredDirect ? "direct" : "unmetered";
}

function circuitSelectLabel(circuit: EnergyCircuitLoadCircuit): string {
  return `K${circuitNoText(circuit.circuitNo)} - ${circuit.description || "Uten kursnavn"}`;
}

function circuitTone(circuit: EnergyCircuitLoadCircuit): string {
  if (circuit.activeLoadCount <= 0) return "empty";
  if (circuit.unmeasuredLoadCount > 0 && circuit.measuredLoadCount > 0) return "partial";
  if (circuit.unmeasuredLoadCount > 0) return "warn";
  if (circuit.measuredLoadCount > 0) return "ok";
  return "empty";
}

function coveragePercent(circuit: EnergyCircuitLoadCircuit): number {
  if (!circuit.activeLoadCount) return 0;
  return Math.round((circuit.measuredLoadCount / circuit.activeLoadCount) * 100);
}

function circuitNoText(circuitNo?: number | null): string {
  if (circuitNo == null) return "?";
  return String(circuitNo).padStart(2, "0");
}

function circuitStats(circuits: EnergyCircuitLoadCircuit[]) {
  const loadCount = circuits.reduce((sum, circuit) => sum + circuit.loadCount, 0);
  const activeLoads = circuits.reduce((sum, circuit) => sum + circuit.activeLoadCount, 0);
  const expectedPowerW = circuits.reduce((sum, circuit) => sum + circuit.expectedPowerW, 0);
  const measuredLoadCount = circuits.reduce((sum, circuit) => sum + circuit.measuredLoadCount, 0);
  const unmeteredLoadCount = circuits.reduce((sum, circuit) => sum + circuit.unmeasuredLoadCount, 0);
  const circuitsWithLoads = circuits.filter((circuit) => circuit.loadCount > 0).length;
  const issueCircuitCount = circuits.filter((circuit) => circuit.unmeasuredLoadCount > 0).length;
  const circuitMeterCount = circuits.filter((circuit) =>
    circuit.measurementGroups.some((group) => group.type === "circuit_meter"),
  ).length;
  return {
    loadCount,
    activeLoads,
    expectedPowerW,
    measuredLoadCount,
    unmeteredLoadCount,
    circuitsWithLoads,
    issueCircuitCount,
    circuitMeterCount,
    measuredPercent: activeLoads ? Math.round((measuredLoadCount / activeLoads) * 100) : 0,
  };
}

function Label({ tone = "default", children }: { tone?: string; children: ReactNode }) {
  return <span className={`energy-tag ${tone}`}>{children}</span>;
}

function SummaryMetric({ label, value, detail, tone }: { label: string; value: string; detail: string; tone?: string }) {
  return (
    <div className={`energy-circuit-summary-metric ${tone || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function deviceMeta(load: EnergyCircuitMeterGroup["loads"][number]): string {
  const parts = [];
  if (load.fibaroDeviceId) parts.push(`dev ${load.fibaroDeviceId}`);
  if (load.fibaroMeterId) parts.push(`måler ${load.fibaroMeterId}`);
  if (load.zwaveSwitchId) parts.push(`sw ${load.zwaveSwitchId}`);
  return parts.join(" · ");
}

function LoadLine({
  circuit,
  group,
  load,
  onEditLoad,
  onAddSimilar,
}: {
  circuit: EnergyCircuitLoadCircuit;
  group: EnergyCircuitMeterGroup;
  load: EnergyCircuitMeterGroup["loads"][number];
  onEditLoad: (circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) => void;
  onAddSimilar: (circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) => void;
}) {
  return (
    <div className={load.active === false ? "energy-load-line inactive" : "energy-load-line"}>
      <div className="energy-load-line-name">
        <strong>{load.name}</strong>
        <span>{[load.loadType, load.area].filter(Boolean).join(" · ") || "Uten type/område"}</span>
      </div>
      <span className={load.fibaroMeterId || load.measuredDirect ? "energy-load-measure ok" : "energy-load-measure warn"}>
        {load.fibaroMeterId ? `Måler ${load.fibaroMeterId}` : load.measuredDirect ? "Direkte" : "Ikke målt"}
      </span>
      <span>{wattText(load.expectedPowerW)}</span>
      <div className="energy-load-line-meta">
        <small>{deviceMeta(load) || "-"}</small>
        <div className="energy-load-actions">
          <button type="button" onClick={() => onEditLoad(circuit, group, load)}>
            Endre
          </button>
          <button type="button" onClick={() => onAddSimilar(circuit, group, load)}>
            Ny lik
          </button>
        </div>
      </div>
    </div>
  );
}

function MeterGroupLine({
  circuit,
  group,
  onAddLoad,
  onEditLoad,
  onAddSimilar,
}: {
  circuit: EnergyCircuitLoadCircuit;
  group: EnergyCircuitMeterGroup;
  onAddLoad: (circuit: EnergyCircuitLoadCircuit, group?: EnergyCircuitMeterGroup | null) => void;
  onEditLoad: (circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) => void;
  onAddSimilar: (circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) => void;
}) {
  return (
    <div className={`energy-meter-line ${group.type}`}>
      <div className="energy-meter-line-head">
        <Label tone={meterTone(group)}>{meterLabel(group)}</Label>
        <div className="energy-meter-line-title">
          <strong>{group.label}</strong>
          <span>{group.meterId ? `HC3 ${group.meterId}` : "Uten ID"} · {group.loadCount} laster</span>
        </div>
        <div className="energy-meter-line-actions">
          <em>{wattText(group.expectedPowerW)}</em>
          <button type="button" onClick={() => onAddLoad(circuit, group)}>
            Ny last
          </button>
        </div>
      </div>
      <div className="energy-meter-line-loads">
        {group.loads.map((load) => (
          <LoadLine
            circuit={circuit}
            group={group}
            load={load}
            key={load.id}
            onEditLoad={onEditLoad}
            onAddSimilar={onAddSimilar}
          />
        ))}
      </div>
    </div>
  );
}

function CircuitRow({
  circuit,
  onAddLoad,
  onEditLoad,
  onAddSimilar,
}: {
  circuit: EnergyCircuitLoadCircuit;
  onAddLoad: (circuit: EnergyCircuitLoadCircuit, group?: EnergyCircuitMeterGroup | null) => void;
  onEditLoad: (circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) => void;
  onAddSimilar: (circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) => void;
}) {
  const tone = circuitTone(circuit);
  const coverage = coveragePercent(circuit);
  const hasLoads = circuit.loadCount > 0;
  return (
    <article className={`energy-circuit-row tone-${tone} ${hasLoads ? "has-loads" : "is-empty"}`}>
      <div className="energy-circuit-row-main">
        <div className="energy-circuit-row-no">K{circuitNoText(circuit.circuitNo)}</div>
        <div className="energy-circuit-row-name">
          <strong>{circuit.description || "Uten kursnavn"}</strong>
          <span>
            {circuit.breaker || "Ukjent vern"}
            {circuit.breakerType ? ` · ${circuit.breakerType}` : ""}
            {circuit.status ? ` · ${circuit.status}` : ""}
          </span>
        </div>
        <div className="energy-circuit-row-status">
          {circuit.isSunbed ? <Label tone="sun">Solseng</Label> : null}
          <Label tone={tone === "empty" ? "default" : tone}>{circuit.measurementMode}</Label>
          <button className="energy-row-action" type="button" onClick={() => onAddLoad(circuit)}>
            Legg til
          </button>
        </div>
        <div className="energy-circuit-row-count">
          <strong>{circuit.activeLoadCount}</strong>
          <span>av {circuit.loadCount} laster</span>
        </div>
        <div className="energy-circuit-row-watts">{wattText(circuit.expectedPowerW)}</div>
        <div className="energy-circuit-row-coverage">
          <div className="energy-circuit-coverage-bar" aria-label={`${coverage}% målt`}>
            <span style={{ width: `${coverage}%` }} />
          </div>
          <small>
            {circuit.activeLoadCount ? `${coverage}% målt` : "ingen last"}
            {circuit.unmeasuredLoadCount ? ` · ${circuit.unmeasuredLoadCount} mangler` : ""}
          </small>
        </div>
      </div>
      {hasLoads ? (
        <div className="energy-circuit-row-detail">
          <p>{circuit.measurementDetail}</p>
          <div className="energy-meter-line-list">
            {circuit.measurementGroups.map((group) => (
              <MeterGroupLine
                circuit={circuit}
                group={group}
                key={group.key}
                onAddLoad={onAddLoad}
                onEditLoad={onEditLoad}
                onAddSimilar={onAddSimilar}
              />
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}

export default function EnergyCircuitLoadsPage({ data, onReload }: { data: ModuleResponse; onReload: () => Promise<unknown> | unknown }) {
  const { message } = AntApp.useApp();
  const [form] = Form.useForm<AddLoadFormValues>();
  const [filter, setFilter] = useState<CircuitFilter>("without-sunbeds");
  const [addState, setAddState] = useState<AddLoadState | null>(null);
  const [savingAdd, setSavingAdd] = useState(false);
  const circuitLoads = data.energyCircuitLoads;
  const circuits = circuitLoads?.circuits ?? [];
  const visibleCircuits = circuits.filter((circuit) => filter === "all" || circuit.isSunbed === (filter === "sunbeds"));
  const stats = circuitStats(visibleCircuits);
  const hiddenCircuitCount = circuits.length - visibleCircuits.length;
  const selectedCircuitNo = Form.useWatch("circuitNo", form);
  const selectedMeterMode = Form.useWatch("meterMode", form);
  const selectedExistingMeterId = Form.useWatch("existingMeterId", form);
  const selectedNewMeterId = Form.useWatch("newMeterId", form);
  const selectedCircuit = useMemo(
    () => circuits.find((circuit) => circuit.circuitNo === selectedCircuitNo) ?? addState?.circuit ?? circuits[0] ?? null,
    [addState?.circuit, circuits, selectedCircuitNo],
  );
  const selectedMeterOptions = useMemo(() => meterOptionsForCircuit(selectedCircuit), [selectedCircuit]);
  const meterUsageById = useMemo(() => meterUsage(circuits), [circuits]);
  const circuitOptions = useMemo(
    () =>
      circuits.map((circuit) => ({
        value: circuit.circuitNo ?? -1,
        label: circuitSelectLabel(circuit),
      })),
    [circuits],
  );
  if (!circuitLoads) return null;

  function meterConflictText(meterId?: number | null) {
    if (meterId == null) return "";
    const usage = meterUsageById.get(Number(meterId)) ?? [];
    if (!usage.length) return "";
    const sameCircuit = usage.some((item) => item.circuit.circuitNo === selectedCircuit?.circuitNo);
    const labels = usage.slice(0, 3).map((item) => `K${circuitNoText(item.circuit.circuitNo)}`).join(", ");
    if (sameCircuit) return `Måler ${meterId} finnes allerede på valgt kurs. Bruk eksisterende måler hvis dette er samme målepunkt.`;
    return `Måler ${meterId} finnes allerede på ${labels}. Kontroller at HC3-ID ikke brukes på feil kurs.`;
  }

  function openAddLoad(circuit?: EnergyCircuitLoadCircuit | null, group?: EnergyCircuitMeterGroup | null) {
    const targetCircuit = circuit ?? visibleCircuits[0] ?? circuits[0] ?? null;
    const meterOptions = meterOptionsForCircuit(targetCircuit);
    const mode = defaultMeterMode(targetCircuit, group);
    const template = group?.loads?.[0] ?? null;
    form.resetFields();
    form.setFieldsValue({
      circuitNo: targetCircuit?.circuitNo ?? null,
      meterMode: mode,
      existingMeterId: group?.meterId ?? meterOptions[0]?.value ?? null,
      newMeterId: null,
      loadType: template?.loadType ?? undefined,
      area: template?.area ?? undefined,
      active: true,
      controllable: false,
      critical: false,
    });
    setAddState({ mode: "create", circuit: targetCircuit, group });
  }

  function openAddSimilar(circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) {
    const meterOptions = meterOptionsForCircuit(circuit);
    const mode = defaultMeterMode(circuit, group);
    form.resetFields();
    form.setFieldsValue({
      circuitNo: circuit.circuitNo ?? null,
      meterMode: mode,
      existingMeterId: load.fibaroMeterId ?? group.meterId ?? meterOptions[0]?.value ?? null,
      newMeterId: mode === "new" ? load.fibaroMeterId ?? null : null,
      name: "",
      loadType: load.loadType ?? undefined,
      area: load.area ?? undefined,
      expectedPowerW: load.expectedPowerW ?? undefined,
      controllable: Boolean(load.controllable),
      critical: Boolean(load.critical),
      active: true,
    });
    setAddState({ mode: "create", circuit, group });
  }

  function openEditLoad(circuit: EnergyCircuitLoadCircuit, group: EnergyCircuitMeterGroup, load: EnergyCircuitLoadItem) {
    const mode = meterModeForLoad(circuit, load);
    form.resetFields();
    form.setFieldsValue({
      circuitNo: circuit.circuitNo ?? null,
      meterMode: mode,
      existingMeterId: load.fibaroMeterId ?? null,
      newMeterId: mode === "new" ? load.fibaroMeterId ?? null : null,
      name: load.name,
      loadType: load.loadType ?? undefined,
      area: load.area ?? undefined,
      expectedPowerW: load.expectedPowerW ?? undefined,
      fibaroDeviceId: load.fibaroDeviceId ?? undefined,
      zwaveSwitchId: load.zwaveSwitchId ?? undefined,
      controllable: Boolean(load.controllable),
      critical: Boolean(load.critical),
      active: load.active !== false,
      note: load.note ?? undefined,
    });
    setAddState({ mode: "edit", circuit, group, load });
  }

  function handleCircuitSelect(circuitNo: number) {
    const circuit = circuits.find((row) => row.circuitNo === circuitNo) ?? null;
    const meterOptions = meterOptionsForCircuit(circuit);
    form.setFieldsValue({
      meterMode: meterOptions.length ? "existing" : "new",
      existingMeterId: meterOptions[0]?.value ?? null,
      newMeterId: null,
    });
    setAddState((current) => (current ? { ...current, circuit, group: null } : { mode: "create", circuit, group: null }));
  }

  function payloadFromValues(values: AddLoadFormValues): EnergyLoadCreateInput {
    const mode = values.meterMode ?? "unmetered";
    const meterId = mode === "existing" ? values.existingMeterId : mode === "new" ? values.newMeterId : null;
    return {
      name: cleanText(values.name) ?? "",
      load_type: cleanText(values.loadType),
      area: cleanText(values.area),
      circuit_no: cleanNumber(values.circuitNo),
      expected_power_w: cleanNumber(values.expectedPowerW),
      measured_direct: mode === "direct",
      fibaro_meter_id: cleanNumber(meterId),
      fibaro_device_id: cleanNumber(values.fibaroDeviceId),
      zwave_switch_id: cleanNumber(values.zwaveSwitchId),
      controllable: Boolean(values.controllable),
      critical: Boolean(values.critical),
      active: values.active !== false,
      note: cleanText(values.note),
    };
  }

  async function saveEnergyLoad(keepOpen = false) {
    if (savingAdd) return;
    const values = await form.validateFields();
    const payload = payloadFromValues(values);
    setSavingAdd(true);
    try {
      const result =
        addState?.mode === "edit" && addState.load
          ? await updateEnergyLoad(addState.load.id, payload as EnergyLoadUpdateInput)
          : await createEnergyLoad(payload);
      message.success(String(result.message || (addState?.mode === "edit" ? "Last er lagret" : "Last er opprettet")));
      await onReload();
      if (keepOpen && addState?.mode === "create") {
        form.setFieldsValue({
          name: "",
          expectedPowerW: undefined,
          fibaroDeviceId: undefined,
          zwaveSwitchId: undefined,
          note: undefined,
          active: true,
        });
        return;
      }
      setAddState(null);
      form.resetFields();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke lagre last");
    } finally {
      setSavingAdd(false);
    }
  }

  const meterModeOptions = [
    ...(selectedMeterOptions.length ? [{ value: "existing", label: "Bruk eksisterende måler på kurset" }] : []),
    { value: "new", label: "Ny HC3-måler / målepunkt" },
    { value: "direct", label: "Direktemålt uten måler-ID" },
    { value: "unmetered", label: "Last uten måler foreløpig" },
  ];
  const activeMeterId = selectedMeterMode === "existing" ? selectedExistingMeterId : selectedMeterMode === "new" ? selectedNewMeterId : null;
  const meterWarningText = selectedMeterMode === "new" ? meterConflictText(activeMeterId) : "";

  return (
    <div className="page-stack energy-circuit-loads-page">
      <section className="work-card energy-circuit-dashboard">
        <div className="energy-circuit-dashboard-main">
          <div>
            <span className="energy-circuit-eyebrow">Energi</span>
            <h2>Kurs/last</h2>
            <p>Kurs med målere, undermålere og laster.</p>
          </div>
          <div className="energy-circuit-measurement-total">
            <span>Dekning</span>
            <strong>{stats.measuredPercent}%</strong>
            <div className="energy-circuit-total-bar" aria-label={`${stats.measuredPercent}% av aktive laster er målt`}>
              <span style={{ width: `${stats.measuredPercent}%` }} />
            </div>
            <small>
              {stats.measuredLoadCount} av {stats.activeLoads} aktive laster har måler
            </small>
          </div>
        </div>

        <div className="energy-circuit-summary-strip">
          <SummaryMetric
            label="Kurser"
            value={String(visibleCircuits.length)}
            detail={`${stats.circuitsWithLoads} med last · ${hiddenCircuitCount} skjult`}
          />
          <SummaryMetric label="Aktive laster" value={String(stats.activeLoads)} detail={`${stats.loadCount} registrert`} />
          <SummaryMetric label="Kursmålt" value={String(stats.circuitMeterCount)} detail="på kursnivå" tone="ok" />
          <SummaryMetric label="Uten måler" value={String(stats.unmeteredLoadCount)} detail={`${stats.issueCircuitCount} kurser bør sjekkes`} tone="warn" />
          <SummaryMetric label="Forventet effekt" value={wattText(stats.expectedPowerW)} detail="registrert for aktive laster" />
        </div>
      </section>

      <section className="work-card energy-circuit-board">
        <div className="energy-circuit-board-title">
          <div>
            <h3>Kursliste</h3>
            <p>
              {visibleCircuits.length} av {circuits.length} kurser vises.
            </p>
          </div>
          <div className="energy-circuit-board-actions">
            <Button type="primary" size="small" onClick={() => openAddLoad()}>
              Ny måler/last
            </Button>
            <div className="energy-circuit-filter" role="group" aria-label="Filtrer kursliste">
              {circuitFilters.map((item) => (
                <button
                  className={filter === item.key ? "active" : ""}
                  key={item.key}
                  onClick={() => setFilter(item.key)}
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="energy-circuit-legend">
              <Label tone="ok">målt</Label>
              <Label tone="partial">delvis</Label>
              <Label tone="warn">mangler måler</Label>
              <Label>ingen last</Label>
            </div>
          </div>
        </div>
        <div className="energy-circuit-board-header" aria-hidden="true">
          <span>Kurs</span>
          <span>Beskrivelse</span>
          <span>Modell</span>
          <span>Laster</span>
          <span>Teori</span>
          <span>Dekning</span>
        </div>
        {visibleCircuits.length ? (
          <div className="energy-circuit-row-list">
            {visibleCircuits.map((circuit) => (
              <CircuitRow
                circuit={circuit}
                key={circuit.key}
                onAddLoad={openAddLoad}
                onEditLoad={openEditLoad}
                onAddSimilar={openAddSimilar}
              />
            ))}
          </div>
        ) : (
          <div className="energy-circuit-empty">Ingen kurser i valgt filter.</div>
        )}
      </section>

      <Modal
        title={addState?.mode === "edit" ? "Rediger last" : "Ny måler og last"}
        open={Boolean(addState)}
        confirmLoading={savingAdd}
        width={900}
        className="energy-add-load-modal"
        onOk={() => saveEnergyLoad(false)}
        onCancel={() => setAddState(null)}
        footer={
          addState
            ? [
                <Button key="cancel" onClick={() => setAddState(null)}>
                  Avbryt
                </Button>,
                addState.mode === "create" ? (
                  <Button key="save-more" loading={savingAdd} onClick={() => saveEnergyLoad(true)}>
                    Opprett og ny
                  </Button>
                ) : null,
                <Button key="save" type="primary" loading={savingAdd} onClick={() => saveEnergyLoad(false)}>
                  {addState.mode === "edit" ? "Lagre" : "Opprett"}
                </Button>,
              ]
            : undefined
        }
        destroyOnHidden
      >
        <Form form={form} layout="vertical" className="energy-add-load-form">
          <div className="energy-add-load-context">
            <span>{addState?.mode === "edit" ? "Redigerer" : "Registreres på"}</span>
            <strong>{selectedCircuit ? circuitSelectLabel(selectedCircuit) : "Velg kurs"}</strong>
            <small>
              {addState?.mode === "edit" && addState.load
                ? `${addState.load.name} kan flyttes mellom kurs, måler og direkte last her.`
                : addState?.group?.label
                ? `Foreslått målepunkt: ${addState.group.label}`
                : "Velg om lasten skal knyttes til eksisterende måler, ny måler eller direkte på kurs."}
            </small>
          </div>

          <div className="energy-add-load-grid">
            <section>
              <h4>Målepunkt</h4>
              <Form.Item name="circuitNo" label="Kurs" rules={[{ required: true, message: "Velg kurs" }]}>
                <Select
                  showSearch
                  optionFilterProp="label"
                  options={circuitOptions}
                  onChange={handleCircuitSelect}
                />
              </Form.Item>
              <Form.Item name="meterMode" label="Målemodell" rules={[{ required: true, message: "Velg målemodell" }]}>
                <Select options={meterModeOptions} />
              </Form.Item>
              {selectedMeterMode === "existing" ? (
                <Form.Item name="existingMeterId" label="Eksisterende måler" rules={[{ required: true, message: "Velg måler" }]}>
                  <Select options={selectedMeterOptions} />
                </Form.Item>
              ) : null}
              {selectedMeterMode === "new" ? (
                <Form.Item name="newMeterId" label="HC3 måler-ID" rules={[{ required: true, message: "Fyll inn HC3 måler-ID" }]}>
                  <InputNumber min={1} precision={0} className="edit-number" />
                </Form.Item>
              ) : null}
              <div className="energy-add-load-help">
                <strong>{selectedMeterMode === "unmetered" ? "Uten måler" : selectedMeterMode === "direct" ? "Direktemålt" : "Målt last"}</strong>
                <span>
                  {selectedMeterMode === "unmetered"
                    ? "Lasten vises som direkte på kurs uten energimåler."
                    : selectedMeterMode === "direct"
                      ? "Lasten markeres som målt, men uten egen HC3 måler-ID."
                      : "Laster med samme HC3 måler-ID samles automatisk under samme målepunkt."}
                </span>
              </div>
              {meterWarningText ? <div className="energy-add-load-warning">{meterWarningText}</div> : null}
            </section>

            <section>
              <h4>Last</h4>
              <Form.Item name="name" label="Navn" rules={[{ required: true, message: "Navn må fylles ut" }]}>
                <Input autoFocus placeholder="For eksempel varmepumpe 1.etg" />
              </Form.Item>
              <div className="energy-add-load-two">
                <Form.Item name="loadType" label="Type">
                  <Input placeholder="lys, ventilasjon, varme..." />
                </Form.Item>
                <Form.Item name="area" label="Område">
                  <Input placeholder="1.etg, VIP, loft..." />
                </Form.Item>
              </div>
              <div className="energy-add-load-three">
                <Form.Item name="expectedPowerW" label="Teoretisk W">
                  <InputNumber min={0} precision={0} className="edit-number" />
                </Form.Item>
                <Form.Item name="fibaroDeviceId" label="HC3 enhet">
                  <InputNumber min={1} precision={0} className="edit-number" />
                </Form.Item>
                <Form.Item name="zwaveSwitchId" label="Z-Wave bryter">
                  <InputNumber min={1} precision={0} className="edit-number" />
                </Form.Item>
              </div>
              <div className="energy-add-load-checks">
                <Form.Item name="active" valuePropName="checked">
                  <Checkbox>Aktiv</Checkbox>
                </Form.Item>
                <Form.Item name="controllable" valuePropName="checked">
                  <Checkbox>Styrbar</Checkbox>
                </Form.Item>
                <Form.Item name="critical" valuePropName="checked">
                  <Checkbox>Kritisk</Checkbox>
                </Form.Item>
              </div>
              <Form.Item name="note" label="Notat">
                <Input.TextArea rows={3} placeholder="Kort teknisk notat ved behov" />
              </Form.Item>
            </section>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
