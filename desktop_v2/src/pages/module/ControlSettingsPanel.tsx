import { App as AntApp, Button, Card, Checkbox, Form, Input, InputNumber, Space, Typography } from "antd";
import { useEffect, useState } from "react";

import { saveConfig, type ControlSettingField, type ControlSettings, type JsonRecord } from "../../api";
import { timeText } from "../ventilation/ventilationHelpers";

function settingInput(field: ControlSettingField) {
  if (field.type === "int" || field.type === "float") {
    return <InputNumber className="edit-number" step={field.type === "float" ? 0.1 : 1} />;
  }
  if (field.type === "time") return <Input type="time" />;
  if (field.type === "bool") return <Checkbox>{field.label}</Checkbox>;
  return <Input />;
}

function fieldLabel(field: ControlSettingField) {
  if (field.type === "bool") return undefined;
  return `${field.label}${field.unit ? ` (${field.unit})` : ""}`;
}

function valueText(value: unknown, unit?: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  return `${String(value)}${unit ? ` ${String(unit)}` : ""}`;
}

export function ControlSettingsPanel({
  settings,
  onReload,
}: {
  settings: ControlSettings;
  onReload: () => void;
}) {
  const { message } = AntApp.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [reason, setReason] = useState("");

  useEffect(() => {
    const values = Object.fromEntries(settings.groups.flatMap((group) => group.fields.map((field) => [field.key, field.value])));
    form.setFieldsValue(values);
  }, [form, settings]);

  async function save() {
    const values = (await form.validateFields()) as JsonRecord;
    setSaving(true);
    try {
      await saveConfig(settings.updateEndpoint, values, reason || `Endret i ${settings.title}`);
      message.success("Innstillinger lagret");
      setReason("");
      await onReload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Lagring feilet");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Space direction="vertical" size={14} className="control-settings-stack">
      <div className="control-settings-head">
        <Card className="summary-card">
          <span>Versjon</span>
          <strong>{settings.version}</strong>
          <small>HC3 leser siste config-versjon</small>
        </Card>
        <Card className="summary-card">
          <span>Endret</span>
          <strong>{timeText(settings.updatedAt)}</strong>
          <small>{settings.updatedBy || "-"}</small>
        </Card>
        <Card className="summary-card">
          <span>API</span>
          <strong>{settings.updateEndpoint}</strong>
          <small>Brukes av runneren i HC3</small>
        </Card>
      </div>

      {settings.summaryRows.length ? (
        <Card className="work-card control-summary-card" title="Reglene som er aktive nå">
          <div className="control-summary-table">
            <div className="control-summary-row control-summary-header">
              <span>Område</span>
              <span>På</span>
              <span>Av</span>
              <span>Tidsvindu</span>
              <span>Merknad</span>
            </div>
            {settings.summaryRows.map((row, index) => (
              <div className="control-summary-row" key={`${String(row.name ?? row.device ?? index)}-${index}`}>
                <strong>{String(row.name ?? "-")}</strong>
                <span>{String(row.start ?? "-")}</span>
                <span>{String(row.stop ?? "-")}</span>
                <span>{String(row.window ?? "-")}</span>
                <span>{String(row.note ?? "-")}</span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      <Form form={form} layout="vertical">
        <div className="control-settings-grid">
          {settings.groups.map((group) => (
            <Card className="work-card control-setting-card" title={group.title} key={group.title}>
              {group.description ? <Typography.Paragraph type="secondary">{group.description}</Typography.Paragraph> : null}
              {group.fields.map((field) => (
                <Form.Item
                  key={field.key}
                  name={field.key}
                  label={fieldLabel(field)}
                  valuePropName={field.type === "bool" ? "checked" : "value"}
                >
                  {settingInput(field)}
                </Form.Item>
              ))}
            </Card>
          ))}
        </div>

        <Card className="work-card control-save-card">
          <Input
            placeholder="Endringsnotat, f.eks. Justert parkering på-grense etter testing"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            onPressEnter={save}
          />
          <Button type="primary" loading={saving} onClick={save}>
            Lagre innstillinger
          </Button>
        </Card>
      </Form>

      <div className="control-info-grid">
        <Card className="work-card" title="Forklaring">
          <ul className="control-rule-list">
            {settings.rules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </Card>
        <Card className="work-card" title="Drift">
          <div className="control-note-list">
            {settings.notes.map((note) => (
              <div className="control-note" key={note.title}>
                <strong>{note.title}</strong>
                <span>{note.text}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {settings.history.length ? (
        <Card className="work-card control-history-card" title="Siste endringer">
          <div className="control-history-table">
            {settings.history.slice(0, 8).map((row, index) => (
              <div className="control-history-row" key={`${String(row.version ?? index)}-${String(row.changed_at ?? index)}`}>
                <strong>v{valueText(row.version)}</strong>
                <span>{timeText(row.changed_at as string | null | undefined)}</span>
                <span>{String(row.changed_by || "-")}</span>
                <span>{String(row.reason || "-")}</span>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </Space>
  );
}
