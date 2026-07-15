import { App as AntApp, Button, Checkbox, Form, Input, InputNumber, Modal, Select } from "antd";
import { useMemo, useState, type ReactNode } from "react";
import {
  createEnergyLoad,
  type EnergyCircuitLoadCircuit,
  type EnergyCircuitMeterGroup,
  type EnergyLoadCreateInput,
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
  circuit?: EnergyCircuitLoadCircuit | null;
  group?: EnergyCircuitMeterGroup | null;
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

function defaultMeterMode(circuit?: EnergyCircuitLoadCircuit | null, group?: EnergyCircuitMeterGroup | null): MeterMode {
  if (group?.meterId != null) return "existing";
  if (group?.type === "direct_meter") return "direct";
  if (group?.type === "unmetered") return "unmetered";
  return meterOptionsForCircuit(circuit).length ? "existing" : "new";
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

function LoadLine({ load }: { load: EnergyCircuitMeterGroup["loads"][number] }) {
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
      <small>{deviceMeta(load) || "-"}</small>
    </div>
  );
}

function MeterGroupLine({
  circuit,
  group,
  onAddLoad,
}: {
  circuit: EnergyCircuitLoadCircuit;
  group: EnergyCircuitMeterGroup;
  onAddLoad: (circuit: EnergyCircuitLoadCircuit, group?: EnergyCircuitMeterGroup | null) => void;
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
          <LoadLine load={load} key={load.id} />
        ))}
      </div>
    </div>
  );
}

function CircuitRow({
  circuit,
  onAddLoad,
}: {
  circuit: EnergyCircuitLoadCircuit;
  onAddLoad: (circuit: EnergyCircuitLoadCircuit, group?: EnergyCircuitMeterGroup | null) => void;
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
              <MeterGroupLine circuit={circuit} group={group} key={group.key} onAddLoad={onAddLoad} />
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
  const selectedCircuit = useMemo(
    () => circuits.find((circuit) => circuit.circuitNo === selectedCircuitNo) ?? addState?.circuit ?? circuits[0] ?? null,
    [addState?.circuit, circuits, selectedCircuitNo],
  );
  const selectedMeterOptions = useMemo(() => meterOptionsForCircuit(selectedCircuit), [selectedCircuit]);
  const circuitOptions = useMemo(
    () =>
      circuits.map((circuit) => ({
        value: circuit.circuitNo ?? -1,
        label: circuitSelectLabel(circuit),
      })),
    [circuits],
  );
  if (!circuitLoads) return null;

  function openAddLoad(circuit?: EnergyCircuitLoadCircuit | null, group?: EnergyCircuitMeterGroup | null) {
    const targetCircuit = circuit ?? visibleCircuits[0] ?? circuits[0] ?? null;
    const meterOptions = meterOptionsForCircuit(targetCircuit);
    const mode = defaultMeterMode(targetCircuit, group);
    form.resetFields();
    form.setFieldsValue({
      circuitNo: targetCircuit?.circuitNo ?? null,
      meterMode: mode,
      existingMeterId: group?.meterId ?? meterOptions[0]?.value ?? null,
      newMeterId: null,
      active: true,
      controllable: false,
      critical: false,
    });
    setAddState({ circuit: targetCircuit, group });
  }

  function handleCircuitSelect(circuitNo: number) {
    const circuit = circuits.find((row) => row.circuitNo === circuitNo) ?? null;
    const meterOptions = meterOptionsForCircuit(circuit);
    form.setFieldsValue({
      meterMode: meterOptions.length ? "existing" : "new",
      existingMeterId: meterOptions[0]?.value ?? null,
      newMeterId: null,
    });
    setAddState((current) => ({ ...current, circuit, group: null }));
  }

  async function saveAddedLoad() {
    if (savingAdd) return;
    const values = await form.validateFields();
    const mode = values.meterMode ?? "unmetered";
    const meterId = mode === "existing" ? values.existingMeterId : mode === "new" ? values.newMeterId : null;
    const payload: EnergyLoadCreateInput = {
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
    setSavingAdd(true);
    try {
      const result = await createEnergyLoad(payload);
      message.success(String(result.message || "Last er opprettet"));
      setAddState(null);
      form.resetFields();
      await onReload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke opprette last");
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
              <CircuitRow circuit={circuit} key={circuit.key} onAddLoad={openAddLoad} />
            ))}
          </div>
        ) : (
          <div className="energy-circuit-empty">Ingen kurser i valgt filter.</div>
        )}
      </section>

      <Modal
        title="Ny måler og last"
        open={Boolean(addState)}
        okText="Opprett"
        cancelText="Avbryt"
        confirmLoading={savingAdd}
        width={900}
        className="energy-add-load-modal"
        onOk={saveAddedLoad}
        onCancel={() => setAddState(null)}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" className="energy-add-load-form">
          <div className="energy-add-load-context">
            <span>Registreres på</span>
            <strong>{selectedCircuit ? circuitSelectLabel(selectedCircuit) : "Velg kurs"}</strong>
            <small>
              {addState?.group?.label
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
