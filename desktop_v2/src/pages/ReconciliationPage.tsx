import {
  CheckCircleFilled,
  ExclamationCircleFilled,
  InfoCircleFilled,
  QuestionCircleFilled,
  WarningFilled,
} from "@ant-design/icons";
import { Link } from "react-router-dom";

import type { ReconciliationCheck, ReconciliationData } from "../api";
import "../styles/reconciliation.css";

type StatusKey = "ok" | "warning" | "critical" | "missing" | "info";

const STATUS_ICON = {
  ok: CheckCircleFilled,
  warning: WarningFilled,
  critical: ExclamationCircleFilled,
  missing: QuestionCircleFilled,
  info: InfoCircleFilled,
};

function statusKey(value: string): StatusKey {
  return (["ok", "warning", "critical", "missing", "info"] as StatusKey[]).includes(value as StatusKey)
    ? (value as StatusKey)
    : "missing";
}

function number(value?: number | null, maximumFractionDigits = 2) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits }).format(value);
}

function dateTime(value?: string | null) {
  if (!value) return "";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("nb-NO", { dateStyle: "short", timeStyle: "short" });
}

function Value({ label, value, unit }: { label: string; value?: number | null; unit?: string }) {
  return (
    <div className="reconciliation-value">
      <span>{label}</span>
      <strong>{number(value)}{value === null || value === undefined || !unit ? "" : ` ${unit}`}</strong>
    </div>
  );
}

function CheckRow({ check }: { check: ReconciliationCheck }) {
  const tone = statusKey(check.status);
  const Icon = STATUS_ICON[tone];
  const content = (
    <>
      <div className={`reconciliation-state tone-${tone}`}>
        <Icon />
        <span>{check.status_label}</span>
      </div>
      <div className="reconciliation-identity">
        <div>
          <span>{check.domain}</span>
          <strong>{check.title}</strong>
        </div>
        <small>{check.period || "Løpende"}</small>
      </div>
      <div className="reconciliation-values">
        <Value label={check.actual_label} value={check.actual_value} unit={check.unit} />
        {check.reference_label ? <Value label={check.reference_label} value={check.reference_value} unit={check.unit} /> : null}
        {check.reference_label ? (
          <div className="reconciliation-value difference">
            <span>Avvik</span>
            <strong>
              {check.difference !== null && check.difference !== undefined && check.difference > 0 ? "+" : ""}
              {number(check.difference)} {check.difference === null || check.difference === undefined ? "" : check.unit}
            </strong>
            {check.difference_percent !== null && check.difference_percent !== undefined ? <small>{number(check.difference_percent)} %</small> : null}
          </div>
        ) : null}
      </div>
      <div className="reconciliation-detail">
        <span>{check.detail}</span>
        {check.updated_at ? <small>Oppdatert {dateTime(check.updated_at)}</small> : null}
      </div>
    </>
  );

  return check.path ? (
    <Link className={`reconciliation-check tone-${tone}`} to={check.path}>
      {content}
    </Link>
  ) : (
    <div className={`reconciliation-check tone-${tone}`}>{content}</div>
  );
}

export default function ReconciliationPage({ data }: { data: ReconciliationData }) {
  const summary = data.summary;
  return (
    <div className="page-stack reconciliation-page">
      <header className="reconciliation-header">
        <div>
          <span>Samlet avstemming</span>
          <strong>{summary.overall_label}</strong>
        </div>
        <small>Oppdatert {dateTime(data.generated_at)}</small>
      </header>

      <section className="reconciliation-summary" aria-label="Kontrollstatus">
        <div className="tone-ok"><span>Stemmer</span><strong>{summary.ok}</strong></div>
        <div className="tone-warning"><span>Kontroller</span><strong>{summary.warning}</strong></div>
        <div className="tone-critical"><span>Avvik</span><strong>{summary.critical}</strong></div>
        <div className="tone-missing"><span>Mangler grunnlag</span><strong>{summary.missing}</strong></div>
      </section>

      {data.groups.map((group) => (
        <section className="reconciliation-group" key={group.id}>
          <header>
            <div>
              <h2>{group.title}</h2>
              <p>{group.description}</p>
            </div>
            <span>{group.summary.attention ? `${group.summary.attention} til kontroll` : "Alt stemmer"}</span>
          </header>
          <div className="reconciliation-list">
            {group.checks.map((check) => <CheckRow check={check} key={check.id} />)}
          </div>
        </section>
      ))}
    </div>
  );
}
