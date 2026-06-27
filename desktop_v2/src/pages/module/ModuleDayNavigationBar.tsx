import { CalendarOutlined } from "@ant-design/icons";
import { Button, Card, Input, Typography } from "antd";

import type { ModuleDayNavigation } from "../../api";
import { PeriodNavigator } from "../../components/PeriodNavigator";

export function ModuleDayNavigationBar({
  navigation,
  onDayChange,
}: {
  navigation: ModuleDayNavigation;
  onDayChange: (day: string) => void;
}) {
  return (
    <Card className="work-card module-day-nav-card">
      <div className="module-day-nav-title">
        <Typography.Text type="secondary">Dato</Typography.Text>
        <Typography.Text strong>{navigation.selectedDayLabel}</Typography.Text>
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
          <Input
            aria-label="Dato"
            className="module-day-nav-date"
            prefix={<CalendarOutlined />}
            size="small"
            type="date"
            value={navigation.selectedDay}
            onChange={(event) => onDayChange(event.target.value)}
          />
        }
      />
    </Card>
  );
}
