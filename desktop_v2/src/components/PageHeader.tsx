import { Typography } from "antd";
import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
  className = "",
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`page-header ${className}`.trim()}>
      <div className="page-header-main">
        {eyebrow ? <Typography.Text className="eyebrow">{eyebrow}</Typography.Text> : null}
        <div className="page-header-title">{title}</div>
        {description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
      </div>
      {meta || actions ? (
        <div className="page-header-side">
          {meta}
          {actions}
        </div>
      ) : null}
    </div>
  );
}
