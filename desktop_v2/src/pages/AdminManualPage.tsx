import { Card, Space, Tag } from "antd";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { fetchAdminManual, type AdminManualArea, type AdminManualChapter, type AdminManualTextItem } from "../api";
import { useApiQuery } from "../hooks";
import "../styles/manual.css";

function ManualAreaCard({ area }: { area: AdminManualArea }) {
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

function ChapterFrame({ chapter, children }: { chapter: AdminManualChapter; children: ReactNode }) {
  return (
    <section className="manual-chapter" id={chapter.id}>
      <div className="manual-chapter-heading">
        <span>{chapter.number}</span>
        <h2>{chapter.title}</h2>
      </div>
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
  items: AdminManualTextItem[];
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

function renderChapter(chapter: AdminManualChapter) {
  if (chapter.paragraphs?.length) {
    return (
      <ChapterFrame chapter={chapter}>
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
      <ChapterFrame chapter={chapter}>
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
      <ChapterFrame chapter={chapter}>
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
      <ChapterFrame chapter={chapter}>
        <TextGrid className="manual-menu-grid" items={chapter.menuGroups} linkable />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  if (chapter.dataSources?.length) {
    return (
      <ChapterFrame chapter={chapter}>
        <TextGrid className="manual-data-grid" items={chapter.dataSources} />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  if (chapter.checklists?.length) {
    return (
      <ChapterFrame chapter={chapter}>
        <TextGrid className="manual-checklist-grid" items={chapter.checklists} linkable />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  if (chapter.troubleshooting?.length) {
    return (
      <ChapterFrame chapter={chapter}>
        <TextGrid className="manual-troubleshooting" items={chapter.troubleshooting} linkable />
        {chapter.note ? <p className="manual-note">{chapter.note}</p> : null}
      </ChapterFrame>
    );
  }

  return null;
}

export default function AdminManualPage() {
  const { data, error, loading } = useApiQuery(["admin-manual"], fetchAdminManual, { staleTime: 10 * 60 * 1000 });

  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock error={error} />;
  if (!data) return null;

  return (
    <Space direction="vertical" size={14} className="page-stack manual-page">
      <PageHeader
        eyebrow="Manual"
        title={data.title}
        description={data.description}
        meta={<Tag color="blue">Build {data.build}</Tag>}
      />

      <div className="manual-layout">
        <aside className="manual-toc">
          <strong>Kapitler</strong>
          <nav>
            {data.chapters.map((chapter) => (
              <a href={`#${chapter.id}`} key={chapter.id}>
                <span>{chapter.number}</span>
                {chapter.title}
              </a>
            ))}
          </nav>
        </aside>

        <main className="manual-document">{data.chapters.map((chapter) => renderChapter(chapter))}</main>
      </div>
    </Space>
  );
}
