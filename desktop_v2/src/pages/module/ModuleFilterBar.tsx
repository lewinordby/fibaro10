import { Button, Card, Input, Select, Space } from "antd";
import { useState } from "react";
import type { ModuleFilter } from "../../api";

function initialFilterValues(filters: ModuleFilter[]): Record<string, string> {
  return Object.fromEntries(filters.map((filter) => [filter.key, filter.value === null || filter.value === undefined ? "" : String(filter.value)]));
}

export function ModuleFilterBar({
  filters,
  onApply,
  onClear,
}: {
  filters: ModuleFilter[];
  onApply: (values: Record<string, string>) => void;
  onClear: (keys: string[]) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => initialFilterValues(filters));
  if (!filters.length) return null;

  function updateValue(key: string, value: string | number | null | undefined) {
    setValues((current) => ({ ...current, [key]: value === null || value === undefined ? "" : String(value) }));
  }

  function submit() {
    onApply(values);
  }

  return (
    <Card className="work-card module-filter-card">
      <div className="module-filter-grid">
        {filters.map((filter) => (
          <label className="module-filter-field" key={filter.key}>
            <span>{filter.label}</span>
            {filter.type === "select" ? (
              <Select
                allowClear
                size="small"
                value={values[filter.key] || undefined}
                options={[{ label: "Alle", value: "" }, ...(filter.options ?? [])]}
                placeholder={filter.placeholder}
                onChange={(value) => updateValue(filter.key, value)}
              />
            ) : (
              <Input
                size="small"
                type={filter.type === "datetime" ? "datetime-local" : filter.type}
                value={values[filter.key] ?? ""}
                placeholder={filter.placeholder}
                onChange={(event) => updateValue(filter.key, event.target.value)}
                onPressEnter={submit}
              />
            )}
          </label>
        ))}
      </div>
      <Space size={8} className="module-filter-actions">
        <Button size="small" type="primary" onClick={submit}>
          Bruk filtre
        </Button>
        <Button size="small" onClick={() => onClear(filters.map((filter) => filter.key))}>
          Nullstill
        </Button>
      </Space>
    </Card>
  );
}
