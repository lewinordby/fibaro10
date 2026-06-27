import { Button, Card, Input, Segmented, Tooltip } from "antd";
import { useMemo } from "react";

import type { ModuleTable, VentilationData } from "../../api";
import { AppChart } from "../../components/AppChart";
import { PeriodNavigator } from "../../components/PeriodNavigator";
import { fanRunSegments, fanSampleRunSegments, formatDayChartTooltip, minuteFromEventX, minuteFromTime, minuteLabel, numberText, percentFromEventX, seriesFocus, type DayChartSample, type DayChartTooltipParam, type VentChartFocus } from "./ventilationHelpers";
export function DayChart({
  ventilation,
  focus,
  onDayChange,
  onFocusChange,
}: {
  ventilation: VentilationData;
  focus: VentChartFocus;
  onDayChange: (day: string) => void;
  onFocusChange: (focus: VentChartFocus) => void;
}) {
  const day = ventilation.day;
  const focusSeries = day.series.filter((series) => seriesFocus(series) === focus);
  const defaultKey = focus === "humidity" ? "humidity_kjeller" : "temp_loft";
  const defaultVisible = Object.fromEntries(focusSeries.map((series) => [series.label, series.key === defaultKey]));
  const yAxisName = focus === "humidity" ? "%" : "C";
  const tooltipUnit = focus === "humidity" ? "%" : " C";
  const chartSamples: DayChartSample[] = day.samples
    .map((sample) => ({ sample, minute: minuteFromTime(sample.time) }))
    .filter((item): item is DayChartSample => item.minute !== null)
    .sort((left, right) => left.minute - right.minute);
  const fanMarkLines = day.fanEvents
    .map((event) => ({
      name: `${event.time} ${event.fan_short} ${event.action}${event.detail ? ` - ${event.detail}` : ""}`,
      xAxis: minuteFromEventX(event.x),
      lineStyle: {
        color: event.color,
        opacity: event.class === "on" ? 0.58 : 0.42,
        type: "dashed",
        width: 1.2,
      },
      label: {
        show: false,
      },
    }))
    .sort((left, right) => Number(left.xAxis) - Number(right.xAxis));

  const option = {
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,0.96)",
      borderColor: "#dbe3ee",
      borderWidth: 1,
      textStyle: { color: "#111827", fontSize: 12 },
      extraCssText: "box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:8px;",
      formatter: (params: DayChartTooltipParam | DayChartTooltipParam[]) => formatDayChartTooltip(params, tooltipUnit),
    },
    legend: {
      top: 0,
      data: focusSeries.map((series) => series.label),
      selected: defaultVisible,
      icon: "roundRect",
      itemWidth: 16,
      itemHeight: 8,
      textStyle: { color: "#475569", fontSize: 12, fontWeight: 650 },
    },
    grid: { top: 48, left: 12, right: 18, bottom: 34, containLabel: true },
    xAxis: {
      type: "value",
      min: 0,
      max: 1440,
      interval: 120,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      axisLabel: { formatter: minuteLabel, color: "#64748b", fontSize: 11 },
      axisPointer: { label: { formatter: (params: { value?: number | string }) => minuteLabel(params.value) } },
      splitLine: { lineStyle: { color: "#edf2f7" } },
    },
    yAxis: {
      type: "value",
      name: yAxisName,
      nameTextStyle: { color: "#64748b", fontSize: 11 },
      axisLabel: { color: "#64748b", fontSize: 11 },
      splitLine: { lineStyle: { color: "#e8edf4" } },
    },
    series: [
      ...focusSeries.map((series) => ({
        name: series.label,
        type: "line",
        data: chartSamples.map(({ sample, minute }) => [minute, typeof sample[series.key] === "number" ? sample[series.key] : null]),
        smooth: true,
        connectNulls: false,
        showSymbol: false,
        lineStyle: { width: 2, color: series.color },
        itemStyle: { color: series.color },
        emphasis: { focus: "series" },
      })),
      {
        name: "__fan_events",
        type: "line",
        data: chartSamples.map(({ minute }) => [minute, null]),
        silent: false,
        tooltip: { show: false },
        symbol: "none",
        lineStyle: { opacity: 0 },
        markLine: {
          animation: false,
          silent: false,
          symbol: ["none", "none"],
          label: { show: false },
          tooltip: {
            show: true,
            formatter: (params: { name?: string }) => params.name || "Viftehendelse",
          },
          data: fanMarkLines,
        },
      },
    ],
  };

  return (
    <Card
      className="chart-card vent-day-card"
      title={focus === "humidity" ? "Dagslogg fuktighet" : "Dagslogg temperatur"}
      extra={
        <Segmented
          className="vent-day-focus"
          size="small"
          value={focus}
          onChange={(value) => onFocusChange(value as VentChartFocus)}
          options={[
            { label: "Temperatur", value: "temperature" },
            { label: "Fuktighet", value: "humidity" },
          ]}
        />
      }
    >
      <div className="vent-day-toolbar">
        <PeriodNavigator
          previousLabel="Forrige dag"
          nextLabel="Neste dag"
          onPrevious={() => onDayChange(day.prevDay)}
          onNext={() => onDayChange(day.nextDay)}
          middle={
            <Button size="small" onClick={() => onDayChange("")}>
              I dag
            </Button>
          }
          extra={
            <Input
              className="vent-date-input"
              type="date"
              value={day.selectedDay}
              onChange={(event) => onDayChange(event.target.value)}
            />
          }
        />
      </div>
      <AppChart key={`${day.selectedDay}-${focus}`} option={option} style={{ height: 360 }} />
      <div className="vent-fan-lanes">
        {day.fans.map((fan) => {
          const events = day.fanEvents.filter((event) => event.fan_key === fan.key);
          const endPercent = day.isToday && typeof day.nowMarker === "number" ? day.nowMarker : 100;
          const fanColor = fan.color || events[0]?.color || "#64748b";
          const fanLabel = fan.short || fan.name;
          const sampleSegments = fanSampleRunSegments(day.samples, fan.sample_attr, fanColor, fanLabel, endPercent);
          const runSegments = sampleSegments.length ? sampleSegments : fanRunSegments(events, endPercent);
          return (
            <div className="vent-fan-lane" key={fan.key}>
              <span>{fanLabel}</span>
              <div className="vent-fan-track">
                {runSegments.map((segment, index) => (
                  <Tooltip key={`${fan.key}-run-${index}`} title={segment.title}>
                    <i
                      className="vent-fan-run"
                      style={{
                        left: `${segment.left}%`,
                        width: `${segment.width}%`,
                        backgroundColor: segment.color,
                        borderColor: segment.color,
                      }}
                      aria-label={segment.title}
                    />
                  </Tooltip>
                ))}
                {events.map((event, index) => (
                  <Tooltip key={`${fan.key}-${event.time}-${index}`} title={`${event.time} ${event.fan_short} ${event.action}${event.detail ? ` - ${event.detail}` : ""}`}>
                    <i
                      className={`vent-fan-event ${event.class}`}
                      style={{
                        left: `${percentFromEventX(event.x)}%`,
                        backgroundColor: event.class === "on" ? event.color : "#ffffff",
                        borderColor: event.color,
                      }}
                      aria-label={`${event.time} ${event.fan_short} ${event.action}${event.detail ? ` - ${event.detail}` : ""}`}
                    />
                  </Tooltip>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function WeatherChart({ table }: { table?: ModuleTable }) {
  const rows = useMemo(() => [...(table?.rows ?? [])].reverse(), [table]);
  if (!rows.length) return null;
  const x = rows.map((row) => {
    const value = row.bucket_start;
    if (typeof value !== "string") return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" });
  });
  const option = {
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,0.96)",
      borderColor: "#dbe3ee",
      borderWidth: 1,
      textStyle: { color: "#111827", fontSize: 12 },
      extraCssText: "box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:8px;",
    },
    legend: {
      top: 0,
      icon: "roundRect",
      itemWidth: 16,
      itemHeight: 8,
      textStyle: { color: "#475569", fontSize: 12, fontWeight: 650 },
    },
    grid: { top: 50, left: 12, right: 18, bottom: 32, containLabel: true },
    xAxis: {
      type: "category",
      data: x,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
      axisLabel: { hideOverlap: true, color: "#64748b", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#64748b", fontSize: 11 },
      splitLine: { lineStyle: { color: "#e8edf4" } },
    },
    series: [
      { name: "Temp", type: "line", data: rows.map((row) => row.air_temperature), showSymbol: false, smooth: true, emphasis: { focus: "series" } },
      { name: "Fukt", type: "line", data: rows.map((row) => row.relative_humidity), showSymbol: false, smooth: true, emphasis: { focus: "series" } },
      { name: "Vind", type: "line", data: rows.map((row) => row.wind_speed), showSymbol: false, smooth: true, emphasis: { focus: "series" } },
      { name: "Skydekke", type: "line", data: rows.map((row) => row.cloud_area_fraction), showSymbol: false, smooth: true, emphasis: { focus: "series" } },
      { name: "Nedbør", type: "bar", data: rows.map((row) => row.precipitation_next_1h) },
    ],
  };
  return (
    <Card className="chart-card vent-weather-card" title="Yr utvikling">
      <AppChart option={option} style={{ height: 330 }} />
    </Card>
  );
}
