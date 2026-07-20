import { ArrowRightOutlined } from "@ant-design/icons";
import { Card, Tag, Typography } from "antd";
import { Link } from "react-router-dom";
import type { ModuleCard } from "../../api";
import { moduleMetricFallbackHref, toneLabel } from "../../domainModel";
import { modulePath } from "../../moduleViews";
import { appPath } from "../../navigation";
import "../../styles/module-metrics.css";

export function ModuleMetric({
  card,
  module,
  view,
}: {
  card: ModuleCard;
  module: string;
  view: string;
}) {
  const rawHref = card.href || moduleMetricFallbackHref(module, view, card);
  const href = rawHref === modulePath(module, view) ? undefined : rawHref;
  const internalPath = appPath(href);
  const content = (
    <Card className={`metric-card module-metric tone-${card.tone ?? "status"}`} hoverable={Boolean(href)}>
      <div className="metric-card-top">
        <Typography.Text className="metric-title">{card.title}</Typography.Text>
        <Tag className="metric-tag">{toneLabel(card.tone, module)}</Tag>
      </div>
      <div className="metric-value-row">
        <span className="metric-value">{card.value}</span>
        {card.unit ? <span className="metric-unit">{card.unit}</span> : null}
      </div>
      <div className="metric-detail">
        <span>{card.detail || "\u00a0"}</span>
        {href ? <ArrowRightOutlined /> : null}
      </div>
    </Card>
  );

  if (!href) return content;
  if (internalPath) {
    return (
      <Link className="card-link" to={internalPath}>
        {content}
      </Link>
    );
  }
  return (
    <a className="card-link" href={href}>
      {content}
    </a>
  );
}
