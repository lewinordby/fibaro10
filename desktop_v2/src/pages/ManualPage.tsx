import { Card, Space, Tag } from "antd";
import type { ReactNode } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import {
  fetchManual,
  type ManualArea,
  type ManualChapter,
  type ManualEnergyDeviceRow,
  type ManualEnergyQuickappGroup,
  type ManualEnergyQuickappReport,
  type ManualEnergyUncoveredMeter,
  type ManualTextItem,
} from "../api";
import { useApiQuery } from "../hooks";
import { modulePath, MODULE_VIEWS } from "../moduleViews";
import "../styles/manual.css";

const MANUAL_CHAPTER_BY_VIEW: Record<string, string> = {
  oversikt: "hva-losningen-er",
  "daglig-bruk": "daglig-bruk",
  menyvalg: "menyvalg",
  okonomi: "okonomi",
  "bygg-drift": "bygg-drift",
  system: "system-underapper",
  datagrunnlag: "datagrunnlag",
  "hc3-energi": "hc3-energi",
  rutiner: "rutiner",
  feilsoking: "feilsoking",
};

const MANUAL_VIEW_SUMMARIES: Record<string, string> = {
  oversikt: "Hva Fibaro10 er, hvilke prinsipper løsningen bygger på, og hvor resten av manualen ligger.",
  "daglig-bruk": "Daglig arbeidsflyt når tall, drift eller datakilder skal kontrolleres.",
  menyvalg: "Forklaring av hovedmenyer og hva de viktigste undersidene brukes til.",
  okonomi: "Omsetning, parkering, soling og kobling mellom bil og SUN2-ID.",
  "bygg-drift": "Energi, ventilasjon, lys, dører, renhold og vedlikehold.",
  system: "Underapper, systemflater og hvordan de henger sammen med hovedappen.",
  datagrunnlag: "Hvilke datakilder løsningen er avhengig av og hva de leverer.",
  "hc3-energi": "Nøyaktig oversikt over HC3 QuickApps for energi, medlemmer og målere som ikke er direkte med.",
  rutiner: "Daglige, ukentlige og månedlige kontrollrutiner.",
  feilsoking: "Praktisk feilsøking når tall, import, grafer eller underapper ikke stemmer.",
};

function ManualAreaCard({ area }: { area: ManualArea }) {
  return (
    <article className={`manual-area-card tone-${area.tone}`}>
      <div className="manual-area-title">
        <span className="manual-area-icon">{area.marker}</span>
        <div>
          <h3>
            <Link to={area.path}>{area.title}</Link>
          </h3>
          <p>{area.purpose}</p>
        </div>
      </div>
      <div className="manual-area-grid">
        <div>
          <strong>Du kan se</strong>
          <ul>
            {area.canSee.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <strong>Du kan gjøre</strong>
          <ul>
            {area.canDo.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  );
}

function ChapterFrame({
  chapter,
  children,
  showHeading = true,
}: {
  chapter: ManualChapter;
  children: ReactNode;
  showHeading?: boolean;
}) {
  return (
    <section className="manual-chapter" id={chapter.id}>
      {showHeading ? (
        <div className="manual-chapter-heading">
          <span>{chapter.number}</span>
          <h2>{chapter.title}</h2>
        </div>
      ) : null}
      {children}
    </section>
  );
}

function TextGrid({
  className,
  items,
  linkable = false,
}: {
  className: string;
  items: ManualTextItem[];
  linkable?: boolean;
}) {
  return (
    <div className={className}>
      {items.map((item) => {
        const content = (
          <>
            <strong>{item.title}</strong>
            <span>{item.text}</span>
          </>
        );
        return linkable && item.path ? (
          <Link to={item.path} key={`${item.title}-${item.path}`}>
            {content}
          </Link>
        ) : (
          <div key={item.title}>{content}</div>
        );
      })}
    </div>
  );
}

function ManualReportStat({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="manual-report-stat">
      <span>{label}</span>
      <strong>{value ?? "-"}</strong>
    </div>
  );
}

function ManualReportStatus({ row }: { row: ManualEnergyUncoveredMeter }) {
  return <span className={`manual-meter-status status-${row.severity || "info"}`}>{row.status}</span>;
}

function ManualGroupTable({ group }: { group: ManualEnergyQuickappGroup }) {
  return (
    <article className="manual-report-group">
      <div className="manual-report-group-head">
        <div>
          <strong>
            {group.id} {group.name}
          </strong>
          <span>
            {group.category} · {group.kind} · {group.memberCount} medlemmer
          </span>
        </div>
        <p>{group.role}</p>
      </div>
      <div className="manual-report-table-wrap">
        <table className="manual-report-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Føler / kanal</th>
              <th>Rom</th>
              <th>Type</th>
              <th>Verdi</th>
              <th>Merknad</th>
            </tr>
          </thead>
          <tbody>
            {group.members.map((member) => (
              <tr key={`${group.id}-${member.id}`}>
                <td>{member.id}</td>
                <td>{member.name}</td>
                <td>{member.room || "-"}</td>
                <td>{member.type || "-"}</td>
                <td>{member.value || "-"}</td>
                <td>{member.dead ? "Død i HC3" : member.note || "Med"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function ManualUncoveredTable({
  rows,
  compact = false,
}: {
  rows: ManualEnergyUncoveredMeter[];
  compact?: boolean;
}) {
  if (!rows.length) return <p className="manual-note">Ingen rader i denne listen.</p>;
  return (
    <div className="manual-report-table-wrap">
      <table className={`manual-report-table ${compact ? "compact" : ""}`}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Føler / kanal</th>
            <th>Parent</th>
            <th>Status</th>
            <th>Dekket av</th>
            <th>Verdi</th>
            <th>Merknad</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.id}-${row.status}`}>
              <td>{row.id}</td>
              <td>
                <strong className="manual-report-cell-title">{row.name}</strong>
                <span className="manual-report-cell-subtitle">{row.type}</span>
              </td>
              <td>
                {row.parentId ? (
                  <>
                    {row.parentId}
                    {row.parentName ? <span className="manual-report-cell-subtitle">{row.parentName}</span> : null}
                  </>
                ) : (
                  "-"
                )}
              </td>
              <td>
                <ManualReportStatus row={row} />
              </td>
              <td>{row.coveredBy || "-"}</td>
              <td>{row.value || "-"}</td>
              <td>{row.note || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ManualAllDevicesTable({ rows }: { rows: ManualEnergyDeviceRow[] }) {
  if (!rows.length) return <p className="manual-note">Ingen komplett enhetsliste er tilgjengelig i inventaret.</p>;
  return (
    <div className="manual-report-table-wrap">
      <table className="manual-report-table all-devices">
        <thead>
          <tr>
            <th>ID</th>
            <th>Enhet</th>
            <th>Parent</th>
            <th>Rom</th>
            <th>Status</th>
            <th>Oppsamling/dekning</th>
            <th>Verdi</th>
            <th>Merknad</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.id ?? "row"}-${index}`}>
              <td>{row.id}</td>
              <td>
                <strong className="manual-report-cell-title">{row.name}</strong>
                <span className="manual-report-cell-subtitle">{row.type || "-"}</span>
                {row.baseType ? <span className="manual-report-cell-subtitle">{row.baseType}</span> : null}
              </td>
              <td>
                {row.parentId ? (
                  <>
                    {row.parentId}
                    {row.parentName ? <span className="manual-report-cell-subtitle">{row.parentName}</span> : null}
                  </>
                ) : (
                  "-"
                )}
              </td>
              <td>{row.room || "-"}</td>
              <td>
                <ManualReportStatus row={row} />
              </td>
              <td>{row.groups || row.coveredBy || "-"}</td>
              <td>{row.value || "-"}</td>
              <td>{row.note || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ManualEnergyQuickappReportView({ report }: { report: ManualEnergyQuickappReport }) {
  return (
    <div className="manual-report">
      <div className="manual-report-stats">
        <ManualReportStat label="QuickApps" value={report.summary.quickApps} />
        <ManualReportStat label="Diff-kontroller" value={report.summary.diffQuickApps} />
        <ManualReportStat label="Direkte medlemmer" value={report.summary.directMembers} />
        <ManualReportStat label="Ikke direkte med" value={report.summary.notDirectlyIncluded} />
        <ManualReportStat label="Reelle hull" value={report.summary.realGaps} />
        <ManualReportStat label="Alle HC3-enheter" value={report.summary.allDevices} />
      </div>

      <TextGrid className="manual-data-grid" items={report.findings} />

      <section className="manual-report-section">
        <h3>Reelle hull og vurderingspunkter</h3>
        <ManualUncoveredTable rows={report.gaps} compact />
      </section>

      <section className="manual-report-section">
        <h3>QuickApps og medlemmer</h3>
        <div className="manual-report-groups">
          {report.groups.map((group) => (
            <ManualGroupTable group={group} key={group.id} />
          ))}
        </div>
      </section>

      <section className="manual-report-section">
        <h3>Alle HC3-enheter i inventaret</h3>
        <p className="manual-note">
          Komplett liste fra HC3 /api/devices. Statusfeltet viser om enheten er direkte med i en oppsamling, dekket
          via samme Z-Wave-node, relevant men ikke med, eller ikke relevant for energisummering.
        </p>
        <ManualAllDevicesTable rows={report.allDevices ?? []} />
      </section>

      <section className="manual-report-section">
        <h3>Alle følere som ikke er direkte med i oppsamling</h3>
        <p className="manual-note">
          Denne listen viser alt HC3 rapporterer som energi-/effektenhet, men som ikke ligger direkte i de åtte
          summerende QuickAppene. Mange av radene er likevel normale underenheter eller skjulte masterkanaler.
        </p>
        <ManualUncoveredTable rows={report.notDirectlyIncluded} />
      </section>

      <p className="manual-note">
        Sist avlest: {report.createdAt || "ukjent"}. Inventarfil: {report.inventoryFile || "mangler"}.
      </p>
    </div>
  );
}

function renderChapter(chapter: ManualChapter, options: { showHeading?: boolean } = {}) {
  const showHeading = options.showHeading ?? true;
  if (chapter.energyQuickappReport) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        <ManualEnergyQuickappReportView report={chapter.energyQuickappReport} />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  if (chapter.paragraphs?.length) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        <Card className="manual-intro-card">
          {chapter.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          {chapter.principles?.length ? (
            <div className="manual-principles">
              {chapter.principles.map((item) => (
                <div key={item.title}>
                  <span className="manual-principle-symbol">{item.marker}</span>
                  <strong>{item.title}</strong>
                  <span>{item.text}</span>
                </div>
              ))}
            </div>
          ) : null}
        </Card>
      </ChapterFrame>
    );
  }

  if (chapter.startLinks?.length || chapter.flow?.length) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        {chapter.startLinks?.length ? (
          <div className="manual-start-grid">
            {chapter.startLinks.map((item) => (
              <Link className="manual-start-link" to={item.path} key={item.path}>
                <strong>{item.label}</strong>
                <span>{item.note}</span>
              </Link>
            ))}
          </div>
        ) : null}
        {chapter.flow?.length ? (
          <div className="manual-flow">
            {chapter.flow.map((item, index) => (
              <div key={item.title}>
                <span>{index + 1}</span>
                <strong>{item.title}</strong>
                <p>{item.text}</p>
              </div>
            ))}
          </div>
        ) : null}
      </ChapterFrame>
    );
  }

  if (chapter.areas?.length) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        <div className="manual-area-list">
          {chapter.areas.map((area) => (
            <ManualAreaCard area={area} key={area.title} />
          ))}
        </div>
        {chapter.subapps?.length ? <TextGrid className="manual-subapps" items={chapter.subapps} /> : null}
      </ChapterFrame>
    );
  }

  if (chapter.menuGroups?.length) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        <TextGrid className="manual-menu-grid" items={chapter.menuGroups} linkable />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  if (chapter.dataSources?.length) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        <TextGrid className="manual-data-grid" items={chapter.dataSources} />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  if (chapter.checklists?.length) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        <TextGrid className="manual-checklist-grid" items={chapter.checklists} linkable />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  if (chapter.troubleshooting?.length) {
    return (
      <ChapterFrame chapter={chapter} showHeading={showHeading}>
        <TextGrid className="manual-troubleshooting" items={chapter.troubleshooting} linkable />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  return null;
}

function ManualSectionIndex({ activeView }: { activeView: string }) {
  return (
    <section className="manual-chapter manual-section-index">
      <div className="manual-chapter-heading">
        <span>→</span>
        <h2>Undersider</h2>
      </div>
      <div className="manual-section-grid">
        {(MODULE_VIEWS.manual ?? []).map((item) => (
          <Link className="manual-section-link" to={modulePath("manual", item.key)} key={item.key}>
            <strong>{item.label}</strong>
            <span>{MANUAL_VIEW_SUMMARIES[item.key] || (item.key === activeView ? "Valgt underside." : "Manualside.")}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default function ManualPage() {
  const { view = "oversikt" } = useParams();
  const chapterId = MANUAL_CHAPTER_BY_VIEW[view];
  const { data, error, loading } = useApiQuery(["manual"], fetchManual, { staleTime: 10 * 60 * 1000 });

  if (!chapterId) return <Navigate to={modulePath("manual")} replace />;

  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock error={error} />;
  if (!data) return null;

  const chapter = data.chapters.find((item) => item.id === chapterId);
  if (!chapter) return <ErrorBlock error={new Error(`Manualkapittel mangler: ${chapterId}`)} />;
  const isOverview = view === "oversikt";

  return (
    <Space direction="vertical" size={14} className="page-stack manual-page">
      <PageHeader
        eyebrow="Manual"
        title={isOverview ? data.title : chapter.title}
        description={MANUAL_VIEW_SUMMARIES[view] || data.description}
        meta={<Tag color="blue">Build {data.build}</Tag>}
      />

      <div className="manual-layout manual-layout-focused">
        <main className="manual-document">
          {renderChapter(chapter, { showHeading: isOverview })}
          {isOverview ? <ManualSectionIndex activeView={view} /> : null}
        </main>
      </div>
    </Space>
  );
}
