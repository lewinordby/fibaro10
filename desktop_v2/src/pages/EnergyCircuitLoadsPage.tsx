import type { ReactNode } from "react";
import type { EnergyCircuitLoadCircuit, EnergyCircuitMeterGroup, ModuleResponse } from "../api";
import { decimal } from "../format";
import "../styles/energy.css";

function wattText(value?: number | null): string {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return `${decimal(Number(value), 0)} W`;
}

function meterLabel(group: EnergyCircuitMeterGroup): string {
  if (group.type === "circuit_meter") return "Kursmåler";
  if (group.type === "shared_meter") return "Felles måler";
  if (group.type === "direct_meter") return "Egen måler";
  return "Uten måler";
}

function meterTone(group: EnergyCircuitMeterGroup): string {
  if (group.type === "circuit_meter") return "ok";
  if (group.type === "shared_meter") return "info";
  if (group.type === "direct_meter") return "energy";
  return "warn";
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
      <span>{wattText(load.expectedPowerW)}</span>
      <small>{deviceMeta(load) || "Ingen enhetskobling"}</small>
    </div>
  );
}

function MeterGroupLine({ group }: { group: EnergyCircuitMeterGroup }) {
  return (
    <div className={`energy-meter-line ${group.type}`}>
      <div className="energy-meter-line-head">
        <Label tone={meterTone(group)}>{meterLabel(group)}</Label>
        {group.meterId ? <span>Måler {group.meterId}</span> : null}
        <strong>{group.label}</strong>
        <em>{wattText(group.expectedPowerW)}</em>
      </div>
      <div className="energy-meter-line-loads">
        {group.loads.map((load) => (
          <LoadLine load={load} key={load.id} />
        ))}
      </div>
    </div>
  );
}

function CircuitRow({ circuit }: { circuit: EnergyCircuitLoadCircuit }) {
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
              <MeterGroupLine group={group} key={group.key} />
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}

export default function EnergyCircuitLoadsPage({ data }: { data: ModuleResponse }) {
  const circuitLoads = data.energyCircuitLoads;
  if (!circuitLoads) return null;
  const circuits = circuitLoads.circuits;
  const summary = circuitLoads.summary;
  const measuredLoads = Math.max(0, summary.activeLoads - summary.unmeteredLoadCount);
  const measuredPercent = summary.activeLoads ? Math.round((measuredLoads / summary.activeLoads) * 100) : 0;
  const circuitsWithLoads = circuits.filter((circuit) => circuit.loadCount > 0).length;
  const emptyCircuits = circuits.length - circuitsWithLoads;
  const issueCircuits = circuits.filter((circuit) => circuit.unmeasuredLoadCount > 0);

  return (
    <div className="page-stack energy-circuit-loads-page">
      <section className="work-card energy-circuit-dashboard">
        <div className="energy-circuit-dashboard-main">
          <div>
            <span className="energy-circuit-eyebrow">Energi</span>
            <h2>Kurs/last</h2>
            <p>Ryddig oversikt over hvilke laster som ligger på hver kurs og hvordan de er dekket av energimålere.</p>
          </div>
          <div className="energy-circuit-measurement-total">
            <span>Målerdekning</span>
            <strong>{measuredPercent}%</strong>
            <div className="energy-circuit-total-bar" aria-label={`${measuredPercent}% av aktive laster er målt`}>
              <span style={{ width: `${measuredPercent}%` }} />
            </div>
            <small>
              {measuredLoads} av {summary.activeLoads} aktive laster har måler
            </small>
          </div>
        </div>

        <div className="energy-circuit-summary-strip">
          <SummaryMetric label="Kurser" value={String(summary.circuits)} detail={`${circuitsWithLoads} med last · ${emptyCircuits} uten`} />
          <SummaryMetric label="Aktive laster" value={String(summary.activeLoads)} detail={`${summary.loads} registrert totalt`} />
          <SummaryMetric label="Kursmålt" value={String(summary.circuitMeterCount)} detail="samme måler dekker kursen" tone="ok" />
          <SummaryMetric label="Uten måler" value={String(summary.unmeteredLoadCount)} detail={`${issueCircuits.length} kurser bør sjekkes`} tone="warn" />
          <SummaryMetric label="Forventet effekt" value={wattText(summary.expectedPowerW)} detail="registrert for aktive laster" />
        </div>
      </section>

      {circuits.length ? (
        <section className="work-card energy-circuit-board">
          <div className="energy-circuit-board-title">
            <div>
              <h3>Kursliste</h3>
              <p>Alle kurser vises i nummerrekkefølge. Laster vises direkte under kursen de tilhører.</p>
            </div>
            <div className="energy-circuit-legend">
              <Label tone="ok">målt</Label>
              <Label tone="partial">delvis</Label>
              <Label tone="warn">mangler måler</Label>
              <Label>ingen last</Label>
            </div>
          </div>
          <div className="energy-circuit-board-header" aria-hidden="true">
            <span>Kurs</span>
            <span>Beskrivelse</span>
            <span>Måling</span>
            <span>Laster</span>
            <span>Effekt</span>
            <span>Dekning</span>
          </div>
          <div className="energy-circuit-row-list">
            {circuits.map((circuit) => (
              <CircuitRow circuit={circuit} key={circuit.key} />
            ))}
          </div>
        </section>
      ) : (
        <div className="work-card energy-circuit-empty">Ingen kurser eller laster er registrert.</div>
      )}
    </div>
  );
}
