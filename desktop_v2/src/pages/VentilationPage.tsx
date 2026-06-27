import { Card, Space, Tag } from "antd";
import { useSearchParams } from "react-router-dom";
import { type ModuleResponse } from "../api";
import { DayChart, WeatherChart } from "./ventilation/VentilationCharts";
import { FilterBar, SettingsView, TableArea } from "./ventilation/VentilationPanels";
import { CompactSnapshot, Snapshot } from "./ventilation/VentilationSnapshot";
import { chartFocusFromSearch, type VentChartFocus } from "./ventilation/ventilationHelpers";

type VentilationPageProps = {
  data: ModuleResponse;
  view: string;
  onReload: () => void;
};

export default function VentilationPage({ data, view, onReload }: VentilationPageProps) {
  const ventilation = data.ventilation;
  const [searchParams, setSearchParams] = useSearchParams();
  if (!ventilation) return null;
  const chartFocus = chartFocusFromSearch(searchParams.get("focus"));

  function setDay(day: string) {
    const next = new URLSearchParams(searchParams);
    if (day) next.set("day", day);
    else next.delete("day");
    setSearchParams(next);
  }

  function setChartFocus(focus: VentChartFocus) {
    const next = new URLSearchParams(searchParams);
    if (focus === "humidity") next.set("focus", "humidity");
    else next.delete("focus");
    setSearchParams(next);
  }

  return (
    <Space direction="vertical" size={16} className="page-stack vent-page">
      {view === "dagslogg" ? <CompactSnapshot ventilation={ventilation} /> : <Snapshot ventilation={ventilation} />}
      {view === "dagslogg" ? <DayChart ventilation={ventilation} focus={chartFocus} onDayChange={setDay} onFocusChange={setChartFocus} /> : null}
      {view === "yr-logg" ? <WeatherChart table={data.tables[0]} /> : null}
      {view === "innstillinger" ? <SettingsView ventilation={ventilation} onReload={onReload} /> : null}
      {view !== "innstillinger" ? <FilterBar filters={data.filters ?? []} /> : null}
      {view === "hendelser" && ventilation.day.fanEvents.length ? (
        <Card className="work-card" title="Dagens viftehendelser">
          <div className="vent-event-list">
            {ventilation.day.fanEvents.slice(-30).reverse().map((event, index) => (
              <div className={`vent-event-row ${event.class}`} key={`${event.time}-${event.fan_key}-${index}`}>
                <strong>{event.time}</strong>
                <span>{event.fan_name}</span>
                {event.class === "on" ? <Tag color="green">PÅ</Tag> : <Tag>AV</Tag>}
                <small>{event.detail}</small>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
      {view !== "innstillinger" ? <TableArea tables={data.tables} /> : null}
    </Space>
  );
}
