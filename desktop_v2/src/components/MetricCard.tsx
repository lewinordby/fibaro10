import { ArrowRightOutlined } from "@ant-design/icons";
import { Card, Tag, Typography } from "antd";
import { Link } from "react-router-dom";
import type { MetricCard as MetricCardData } from "../api";
import { toneLabel } from "../domainModel";
import { appPath } from "../navigation";

export default function MetricCard({ card }: { card: MetricCardData }) {
  const internalPath = appPath(card.href);
  const content = (
    <Card className={`metric-card tone-${card.tone ?? "status"}`} hoverable={Boolean(card.href)}>
      <div className="metric-card-top">
        <Typography.Text className="metric-title">{card.title}</Typography.Text>
        <Tag className="metric-tag">{toneLabel(card.tone, card.group)}</Tag>
      </div>
      <div className="metric-value-row">
        <span className="metric-value">{card.value}</span>
        {card.unit ? <span className="metric-unit">{card.unit}</span> : null}
      </div>
      <div className="metric-detail">
        <span>{card.detail || "\u00a0"}</span>
        {card.href ? <ArrowRightOutlined /> : null}
      </div>
    </Card>
  );

  if (!card.href) return content;
  if (internalPath) {
    return (
      <Link className="card-link" to={internalPath}>
        {content}
      </Link>
    );
  }
  return (
    <a className="card-link" href={card.href}>
      {content}
    </a>
  );
}
