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
  return "Direkte på kurs";
}

function meterTone(group: EnergyCircuitMeterGroup): string {
  if (group.type === "circuit_meter") return "ok";
  if (group.type === "shared_meter") return "info";
  if (group.type === "direct_meter") return "energy";
  return "default";
}

function circuitStatusColor(circuit: EnergyCircuitLoadCircuit): string {
  if (circuit.unmeasuredLoadCount > 0) return "warn";
  if (circuit.measuredLoadCount > 0) return "ok";
  return "default";
}

function Label({ tone = "default", children }: { tone?: string; children: ReactNode }) {
  return <span className={`energy-tag ${tone}`}>{children}</span>;
}

function LoadPill({ load }: { load: EnergyCircuitMeterGroup["loads"][number] }) {
  return (
    <div className={load.active === false ? "energy-load-pill inactive" : "energy-load-pill"}>
      <div>
        <strong>{load.name}</strong>
        <span>{[load.loadType, load.area].filter(Boolean).join(" · ") || "Uten type/område"}</span>
      </div>
      <div className="energy-load-pill-meta">
        <span>{wattText(load.expectedPowerW)}</span>
        {load.fibaroDeviceId ? <Label>dev {load.fibaroDeviceId}</Label> : null}
        {load.zwaveSwitchId ? <Label>sw {load.zwaveSwitchId}</Label> : null}
      </div>
    </div>
  );
}

function MeterGroup({ group, circuitExpectedPower }: { group: EnergyCircuitMeterGroup; circuitExpectedPower: number }) {
  const percent = circuitExpectedPower > 0 ? Math.min(100, Math.round((group.expectedPowerW / circuitExpectedPower) * 100)) : 0;
  return (
    <section className={`energy-meter-group ${group.type}`}>
      <div className="energy-meter-group-head">
        <div>
          <Label tone={meterTone(group)}>{meterLabel(group)}</Label>
          {group.meterId ? <Label tone="info">måler {group.meterId}</Label> : null}
          <strong>{group.label}</strong>
        </div>
        <span>{wattText(group.expectedPowerW)}</span>
      </div>
      <div className="energy-meter-progress" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="energy-load-list">
        {group.loads.map((load) => (
          <LoadPill load={load} key={load.id} />
        ))}
      </div>
    </section>
  );
}

function CircuitCard({ circuit }: { circuit: EnergyCircuitLoadCircuit }) {
  return (
    <article className="work-card energy-circuit-card">
      <div className="energy-circuit-head">
        <div className="energy-circuit-title">
          <span className="energy-circuit-no">{circuit.circuitNo ?? "-"}</span>
          <div>
            <h3>{circuit.description || "Uten kursnavn"}</h3>
            <p>
              {circuit.breaker || "Ukjent vern"}
              {circuit.breakerType ? ` · ${circuit.breakerType}` : ""}
              {circuit.status ? ` · ${circuit.status}` : ""}
            </p>
          </div>
        </div>
        <div className="energy-circuit-badges">
          {circuit.isSunbed ? <Label tone="sun">Solsengkurs</Label> : null}
          <Label tone={circuitStatusColor(circuit)}>{circuit.measurementMode}</Label>
        </div>
      </div>

      <div className="energy-circuit-facts">
        <span>
          <small>Laster</small>
          <strong>{circuit.activeLoadCount}/{circuit.loadCount}</strong>
        </span>
        <span>
          <small>Forventet</small>
          <strong>{wattText(circuit.expectedPowerW)}</strong>
        </span>
        <span>
          <small>Målt</small>
          <strong>{circuit.measuredLoadCount}</strong>
        </span>
        <span>
          <small>Uten måler</small>
          <strong>{circuit.unmeasuredLoadCount}</strong>
        </span>
      </div>

      <p className="energy-circuit-detail">{circuit.measurementDetail}</p>

      <div className="energy-meter-groups">
        {circuit.measurementGroups.map((group) => (
          <MeterGroup group={group} circuitExpectedPower={circuit.expectedPowerW} key={group.key} />
        ))}
      </div>
    </article>
  );
}

export default function EnergyCircuitLoadsPage({ data }: { data: ModuleResponse }) {
  const circuitLoads = data.energyCircuitLoads;
  if (!circuitLoads) return null;
  const circuits = circuitLoads.circuits;
  const summary = circuitLoads.summary;

  return (
    <div className="page-stack energy-circuit-loads-page">
      <section className="work-card energy-circuit-loads-intro">
        <div>
          <span className="energy-circuit-loads-icon">K</span>
          <div>
            <strong>Kurs/last viser praktisk måledekning.</strong>
            <span>
              En kurs kan ha én måler som dekker alt, flere laster på samme måler, egne målere per last,
              eller laster som foreløpig bare ligger direkte på kursen.
            </span>
          </div>
        </div>
        <div>
          <span className="energy-circuit-loads-icon">W</span>
          <span>{wattText(circuitLoads.summary.expectedPowerW)} registrert forventet effekt</span>
        </div>
        <div className="energy-circuit-loads-summary">
          <span>{summary.circuits} kurser</span>
          <span>{summary.activeLoads} aktive laster</span>
          <span>{summary.circuitMeterCount} kursmålt</span>
          <span>{summary.unmeteredLoadCount} uten måler</span>
        </div>
      </section>

      {circuits.length ? (
        <div className="energy-circuit-grid">
          {circuits.map((circuit) => (
            <CircuitCard circuit={circuit} key={circuit.key} />
          ))}
        </div>
      ) : (
        <div className="work-card energy-circuit-empty">Ingen kurser eller laster er registrert.</div>
      )}
    </div>
  );
}
