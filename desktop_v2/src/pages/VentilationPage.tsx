import { App as AntApp, Button, Card, Form, Input, InputNumber, Space, Tabs, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { saveConfig, type ModuleFilter, type ModuleResponse, type ModuleTable, type VentilationData, type VentilationSettingField } from "../api";
import { DayChart, WeatherChart } from "./ventilation/VentilationCharts";
import { CompactSnapshot, Snapshot } from "./ventilation/VentilationSnapshot";
import { VentilationTable, chartFocusFromSearch, filterRows, timeText, type VentChartFocus } from "./ventilation/ventilationHelpers";

type VentilationPageProps = {
  data: ModuleResponse;
  view: string;
  onReload: () => void;
};

function FilterBar({ filters }: { filters: ModuleFilter[] }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const filterKey = searchParams.toString();
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    setValues(Object.fromEntries(filters.map((filter) => [filter.key, filter.value === null || filter.value === undefined ? "" : String(filter.value)])));
  }, [filterKey, filters]);

  if (!filters.length) return null;

  function apply() {
    const next = new URLSearchParams(searchParams);
    Object.entries(values).forEach(([key, value]) => {
      const trimmed = value.trim();
      if (trimmed) next.set(key, trimmed);
      else next.delete(key);
    });
    setSearchParams(next);
  }

  function clear() {
    const next = new URLSearchParams(searchParams);
    filters.forEach((filter) => next.delete(filter.key));
    setSearchParams(next);
  }

  return (
    <Card className="work-card module-filter-card">
      <div className="module-filter-grid">
        {filters.map((filter) => (
          <label className="module-filter-field" key={filter.key}>
            <span>{filter.label}</span>
            <Input
              size="small"
              type={filter.type === "datetime" ? "datetime-local" : filter.type}
              value={values[filter.key] ?? ""}
              onChange={(event) => setValues((current) => ({ ...current, [filter.key]: event.target.value }))}
              onPressEnter={apply}
            />
          </label>
        ))}
      </div>
      <Space size={8} className="module-filter-actions">
        <Button size="small" type="primary" onClick={apply}>
          Bruk filtre
        </Button>
        <Button size="small" onClick={clear}>
          Nullstill
        </Button>
      </Space>
    </Card>
  );
}

function settingInput(field: VentilationSettingField) {
  if (field.type === "int" || field.type === "float") return <InputNumber className="edit-number" step={field.type === "float" ? 0.1 : 1} />;
  if (field.type === "time") return <Input type="time" />;
  return <Input />;
}

function SettingsView({ ventilation, onReload }: { ventilation: VentilationData; onReload: () => void }) {
  const settings = ventilation.settings;
  const { message } = AntApp.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!settings) return;
    const values = Object.fromEntries(settings.groups.flatMap((group) => group.fields.map((field) => [field.key, field.value])));
    form.setFieldsValue(values);
  }, [form, settings]);

  if (!settings) return null;
  const activeSettings = settings;

  async function save() {
    const values = (await form.validateFields()) as Record<string, unknown>;
    setSaving(true);
    try {
      await saveConfig(activeSettings.updateEndpoint, values, reason || "Endret i ventilasjonssiden");
      message.success("Ventilasjonsinnstillinger lagret");
      setReason("");
      onReload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Lagring feilet");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Space direction="vertical" size={14} className="vent-stack">
      <div className="vent-settings-head">
        <Card className="summary-card">
          <span>Versjon</span>
          <strong>{settings.version}</strong>
          <small>Oppdatert {timeText(settings.updatedAt)}</small>
        </Card>
        <Card className="summary-card">
          <span>Endret av</span>
          <strong>{settings.updatedBy || "-"}</strong>
          <small>HC3 henter via config API</small>
        </Card>
      </div>
      <Form form={form} layout="vertical">
        <div className="vent-settings-grid">
          {settings.groups.map((group) => (
            <Card className="work-card vent-setting-card" title={group.title} key={group.title}>
              {group.description ? <Typography.Paragraph type="secondary">{group.description}</Typography.Paragraph> : null}
              {group.fields.map((field) => (
                <Form.Item key={field.key} name={field.key} label={`${field.label}${field.unit ? ` (${field.unit})` : ""}`}>
                  {settingInput(field)}
                </Form.Item>
              ))}
            </Card>
          ))}
        </div>
        <Card className="work-card vent-save-card">
          <Input
            placeholder="Endringsnotat"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <Button type="primary" loading={saving} onClick={save}>
            Lagre innstillinger
          </Button>
        </Card>
      </Form>
      <Card className="work-card" title="Aktive regler">
        <ul className="vent-rule-list">
          {settings.rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </Card>
    </Space>
  );
}

function TableArea({ tables }: { tables: ModuleTable[] }) {
  const [draftQuery, setDraftQuery] = useState("");
  const [query, setQuery] = useState("");
  if (!tables.length) return null;
  return (
    <Card className="table-card module-table-card">
      <div className="table-toolbar">
        <Input.Search
          allowClear
          placeholder="Søk i tabellene"
          value={draftQuery}
          onChange={(event) => {
            setDraftQuery(event.target.value);
            if (!event.target.value) setQuery("");
          }}
          onSearch={(value) => setQuery(value.trim())}
          enterButton="Søk"
        />
      </div>
      <Tabs
        items={tables.map((table) => ({
          key: table.title,
          label: (
            <span>
              {table.title}
              <span className="tab-count">{filterRows(table.rows, table.columns, query).length}</span>
            </span>
          ),
          children: <VentilationTable table={table} query={query} />,
        }))}
      />
    </Card>
  );
}

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
