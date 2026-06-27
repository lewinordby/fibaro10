import { App as AntApp, Button, Card, Form, Input, InputNumber, Space, Tabs, Typography } from "antd";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { saveConfig, type ModuleFilter, type ModuleTable, type VentilationData, type VentilationSettingField } from "../../api";
import { VentilationTable, filterRows, timeText } from "./ventilationHelpers";
export function FilterBar({ filters }: { filters: ModuleFilter[] }) {
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

export function SettingsView({ ventilation, onReload }: { ventilation: VentilationData; onReload: () => void }) {
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

export function TableArea({ tables }: { tables: ModuleTable[] }) {
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
