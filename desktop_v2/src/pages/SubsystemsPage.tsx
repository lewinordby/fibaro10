import {
  AppstoreOutlined,
  CloudOutlined,
  GlobalOutlined,
  HeartOutlined,
  LinkOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { Button, Input, Segmented, Space, Tag } from "antd";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSystemSubsystems, type SystemSubsystem } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/system-pages.css";

type AccessFilter = "all" | "external" | "local" | "internal";

const ACCESS_LABELS: Record<SystemSubsystem["access"], string> = {
  external: "Ekstern",
  local: "Internt nett",
  internal: "Intern tjeneste",
};

function accessColor(access: SystemSubsystem["access"]) {
  if (access === "external") return "blue";
  if (access === "local") return "cyan";
  return "default";
}

function SubsystemItem({ subsystem }: { subsystem: SystemSubsystem }) {
  const title = subsystem.primary_url ? (
    <a href={subsystem.primary_url} target="_blank" rel="noreferrer">
      {subsystem.title}
    </a>
  ) : (
    subsystem.title
  );
  return (
    <article className="subsystem-item">
      <div className="subsystem-item-main">
        <div className="subsystem-item-icon" aria-hidden="true">
          {subsystem.access === "external" ? <GlobalOutlined /> : <AppstoreOutlined />}
        </div>
        <div>
          <div className="subsystem-item-title">
            <h3>{title}</h3>
            <Tag color={accessColor(subsystem.access)}>{ACCESS_LABELS[subsystem.access]}</Tag>
            <Tag>{subsystem.status}</Tag>
          </div>
          <p>{subsystem.role}</p>
        </div>
      </div>
      <div className="subsystem-item-meta">
        <span>{subsystem.runtime}</span>
        {subsystem.compose_service ? <code>{subsystem.compose_service}</code> : null}
        <span>{subsystem.criticality}</span>
      </div>
      <div className="subsystem-item-actions">
        {subsystem.links.map((link) => (
          <Button
            key={`${link.kind}-${link.url}`}
            type={link.kind === "public" ? "primary" : "default"}
            icon={link.kind === "health" ? <HeartOutlined /> : link.kind === "public" ? <GlobalOutlined /> : <LinkOutlined />}
            href={link.url}
            target="_blank"
            rel="noreferrer"
          >
            {link.label}
          </Button>
        ))}
        {!subsystem.links.length ? (
          <Link to="/admin/systemkart">
            <Button icon={<LinkOutlined />}>Se i systemkart</Button>
          </Link>
        ) : null}
      </div>
    </article>
  );
}

export default function SubsystemsPage() {
  const { data, loading, error } = useApiQuery(queryKeys.systemSubsystems(), fetchSystemSubsystems);
  const [access, setAccess] = useState<AccessFilter>("all");
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("nb-NO");
    const rows = (data?.subsystems ?? []).filter((row) => {
      if (access !== "all" && row.access !== access) return false;
      if (!normalizedQuery) return true;
      return [row.title, row.component, row.area, row.role, row.compose_service]
        .join(" ")
        .toLocaleLowerCase("nb-NO")
        .includes(normalizedQuery);
    });
    const grouped = new Map<string, SystemSubsystem[]>();
    rows.forEach((row) => grouped.set(row.area, [...(grouped.get(row.area) ?? []), row]));
    return [...grouped.entries()]
      .sort(([left], [right]) => left.localeCompare(right, "nb"))
      .map(([area, items]) => ({ area, items: items.sort((left, right) => left.title.localeCompare(right.title, "nb")) }));
  }, [access, data?.subsystems, query]);

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack system-hub-page subsystems-page">
      <PageHeader
        eyebrow="System"
        title="Undersystemer"
        description="Ett sted for å åpne alle grensesnitt, lokale tjenester og helsesjekker som Fibaro10 er avhengig av."
        actions={
          <Link to="/admin/systemkart">
            <Button icon={<LinkOutlined />}>Teknisk systemkart</Button>
          </Link>
        }
      />

      <section className="system-summary-strip" aria-label="Systemoversikt">
        <div>
          <span>Komponenter</span>
          <strong>{data.summary.components}</strong>
        </div>
        <div>
          <span>Webflater</span>
          <strong>{data.summary.web_interfaces}</strong>
        </div>
        <div>
          <span>Kritiske / høye</span>
          <strong>{data.summary.critical}</strong>
        </div>
        <div className="system-summary-explanation">
          <CloudOutlined />
          <span>Eksterne lenker virker over internett. Lokale lenker krever tilgang til det interne nettet.</span>
        </div>
      </section>

      <div className="subsystem-toolbar">
        <Segmented<AccessFilter>
          value={access}
          onChange={setAccess}
          options={[
            { label: "Alle", value: "all" },
            { label: "Eksterne", value: "external" },
            { label: "Internt nett", value: "local" },
            { label: "Interne tjenester", value: "internal" },
          ]}
        />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Søk etter app eller tjeneste"
          aria-label="Søk etter undersystem"
        />
      </div>

      {groups.length ? (
        <div className="subsystem-groups">
          {groups.map((group) => (
            <section className="subsystem-group" key={group.area}>
              <div className="subsystem-group-heading">
                <h2>{group.area}</h2>
                <span>{group.items.length}</span>
              </div>
              <div className="subsystem-grid">
                {group.items.map((subsystem) => (
                  <SubsystemItem key={subsystem.component} subsystem={subsystem} />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="system-empty-result">Ingen undersystemer passer med filteret.</div>
      )}
    </Space>
  );
}
