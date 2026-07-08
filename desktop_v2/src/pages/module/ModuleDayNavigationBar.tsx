import { CalendarOutlined } from "@ant-design/icons";
import { Button, Card, Input, Space, Typography } from "antd";

import type { ModuleAction, ModuleDayNavigation } from "../../api";
import { PeriodNavigator } from "../../components/PeriodNavigator";

export function ModuleDayNavigationBar({
  navigation,
  actions = [],
  runningAction,
  onDayChange,
  onAction,
}: {
  navigation: ModuleDayNavigation;
  actions?: ModuleAction[];
  runningAction?: string | null;
  onDayChange: (day: string) => void;
  onAction?: (action: ModuleAction) => void;
}) {
  return (
    <Card className="work-card module-day-nav-card">
      <div className="module-day-nav-title">
        <Typography.Text type="secondary">{navigation.context?.label ?? "Dato"}</Typography.Text>
        <Typography.Text strong>{navigation.context?.value ?? navigation.selectedDayLabel}</Typography.Text>
        {navigation.context?.detail ? <small>{navigation.context.detail}</small> : null}
      </div>
      <PeriodNavigator
        className="module-day-nav-actions"
        previousLabel="Forrige dag"
        nextLabel="Neste dag"
        onPrevious={() => onDayChange(navigation.prevDay)}
        onNext={() => onDayChange(navigation.nextDay)}
        middle={
          <Button size="small" onClick={() => onDayChange("")}>
            I dag
          </Button>
        }
        extra={
          <Space size={6} wrap>
            <Input
              aria-label="Dato"
              className="module-day-nav-date"
              prefix={<CalendarOutlined />}
              size="small"
              type="date"
              value={navigation.selectedDay}
              onChange={(event) => onDayChange(event.target.value)}
            />
            {actions.map((action) => (
              <Button
                key={action.key}
                loading={runningAction === action.key}
                disabled={Boolean(runningAction && runningAction !== action.key)}
                size="small"
                type={action.tone === "primary" ? "primary" : "default"}
                onClick={() => onAction?.(action)}
              >
                {action.label}
              </Button>
            ))}
          </Space>
        }
      />
    </Card>
  );
}
