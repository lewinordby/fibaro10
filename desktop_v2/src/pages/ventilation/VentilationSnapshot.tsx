import { Card, Space, Tooltip, Typography } from "antd";

import type { VentilationData } from "../../api";
import { numberText, stateTag, timeText } from "./ventilationHelpers";
export function Snapshot({ ventilation }: { ventilation: VentilationData }) {
  return (
    <Space direction="vertical" size={12} className="vent-stack">
      <div className="vent-current-row">
        {ventilation.latest.groups.map((group) => (
          <Card className={`work-card vent-zone-card zone-${group.key}`} key={group.key} title={group.title}>
            <div className="vent-zone-grid">
              {group.fields.map((field) => (
                <div className="vent-reading" key={field.key}>
                  <span>{field.label}</span>
                  <strong>{numberText(field.temperature)} C</strong>
                  <small>{field.humidity !== null && field.humidity !== undefined ? `${numberText(field.humidity, 0)}%` : field.detail || "-"}</small>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
      <Card className="work-card vent-state-card">
        <div className="vent-state-head">
          <div>
            <Typography.Text className="eyebrow">Siste ventilasjonssample</Typography.Text>
            <strong>{timeText(ventilation.latest.bucketStart)}</strong>
            <span>{ventilation.latest.mode || "-"}</span>
          </div>
          <div className="vent-weather-line">
            <strong>{ventilation.latest.weather.text || "-"}</strong>
            <span>
              {numberText(ventilation.latest.weather.airTemperature)} C / {numberText(ventilation.latest.weather.relativeHumidity, 0)}% / vind{" "}
              {numberText(ventilation.latest.weather.windSpeed)} m/s
            </span>
          </div>
        </div>
        <div className="vent-fan-strip">
          {ventilation.latest.fans.map((fan) => (
            <span className="vent-fan-pill" key={fan.key}>
              {fan.label}
              {stateTag(fan.state)}
            </span>
          ))}
        </div>
      </Card>
    </Space>
  );
}

export function CompactSnapshot({ ventilation }: { ventilation: VentilationData }) {
  const readings = ventilation.latest.groups.flatMap((group) => group.fields.map((field) => ({ ...field, group: group.title })));
  return (
    <Card className="work-card vent-compact-card">
      <div className="vent-compact-main">
        <div className="vent-compact-sample">
          <Typography.Text className="eyebrow">Siste sample</Typography.Text>
          <strong>{timeText(ventilation.latest.bucketStart)}</strong>
          <span className="vent-mode-chip">{ventilation.latest.mode || "-"}</span>
        </div>
        <div className="vent-compact-readings">
          {readings.map((field) => (
            <Tooltip key={`${field.group}-${field.key}`} title={`${field.group}: ${field.label}`}>
              <span className="vent-compact-reading">
                <small>{field.label}</small>
                <strong>{numberText(field.temperature)} C</strong>
                <em>{field.humidity !== null && field.humidity !== undefined ? `${numberText(field.humidity, 0)}%` : field.detail || "-"}</em>
              </span>
            </Tooltip>
          ))}
        </div>
        <div className="vent-compact-weather">
          <Typography.Text className="eyebrow">Yr nå</Typography.Text>
          <strong>{ventilation.latest.weather.text || "-"}</strong>
          <span>
            {numberText(ventilation.latest.weather.airTemperature)} C / {numberText(ventilation.latest.weather.relativeHumidity, 0)}% / vind{" "}
            {numberText(ventilation.latest.weather.windSpeed)} m/s
          </span>
        </div>
      </div>
      <div className="vent-compact-fans">
        {ventilation.latest.fans.map((fan) => (
          <span className="vent-fan-pill" key={fan.key}>
            {fan.label}
            {stateTag(fan.state)}
          </span>
        ))}
      </div>
    </Card>
  );
}
