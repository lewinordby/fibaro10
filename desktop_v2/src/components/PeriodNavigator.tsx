import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { Button, Space } from "antd";
import type { SizeType } from "antd/es/config-provider/SizeContext";
import type { ReactNode } from "react";

export function PeriodNavigator({
  previousLabel = "Forrige",
  previousTitle,
  nextLabel = "Neste",
  nextTitle,
  canNext = true,
  size = "small",
  middle,
  extra,
  className = "",
  onPrevious,
  onNext,
}: {
  previousLabel?: ReactNode;
  previousTitle?: string;
  nextLabel?: ReactNode;
  nextTitle?: string;
  canNext?: boolean;
  size?: SizeType;
  middle?: ReactNode;
  extra?: ReactNode;
  className?: string;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <Space size={8} wrap className={`period-navigator ${className}`.trim()}>
      <Space.Compact className="period-navigator-step">
        <Button size={size} icon={<LeftOutlined />} onClick={onPrevious} title={previousTitle}>
          {previousLabel}
        </Button>
        {middle}
        <Button size={size} disabled={!canNext} icon={<RightOutlined />} onClick={onNext} title={nextTitle}>
          {nextLabel}
        </Button>
      </Space.Compact>
      {extra}
    </Space>
  );
}

export function PeriodLabel({ children }: { children: ReactNode }) {
  return <div className="period-navigator-current">{children}</div>;
}
