import { Card, Space, Tag } from "antd";
import type { ReactNode } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { fetchManual, type ManualArea, type ManualChapter, type ManualTextItem } from "../api";
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

function renderChapter(chapter: ManualChapter, options: { showHeading?: boolean } = {}) {
  const showHeading = options.showHeading ?? true;
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
