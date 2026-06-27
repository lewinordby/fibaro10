import { Button, Space, Table, Typography } from "antd";
import { useMemo } from "react";
import type { ReactNode } from "react";

import type { ModuleEditConfig, ModuleRow, ModuleTable } from "../../api";
import { countText, filterRows, moduleColumns, tableRowKey } from "./moduleTableUtils";

export function tabLabel(table: ModuleTable, query: string): ReactNode {
  const filteredCount = filterRows(table.rows, table.columns, query).length;
  return (
    <span>
      {table.title}
      <span className="tab-count">{query.trim() ? `${filteredCount}/${table.rows.length}` : table.rows.length}</span>
    </span>
  );
}

export function tableSearchPlaceholder(module: string, view: string): string {
  if (module === "parkering" && view === "kjoretoy") return "SÃ¸k etter reg.nr, bil, eier, omrÃ¥de. Bruk \"nordby\" for eksakt ord.";
  return "SÃ¸k i tabellene";
}

export function ModuleTablePane({
  table,
  query,
  onEdit,
}: {
  table: ModuleTable;
  query: string;
  onEdit?: (edit: ModuleEditConfig, row: ModuleRow, create?: boolean) => void;
}) {
  const columns = useMemo(() => moduleColumns(table, onEdit), [onEdit, table]);
  const filteredRows = useMemo(() => filterRows(table.rows, table.columns, query), [query, table.columns, table.rows]);
  const tableRows = useMemo(
    () =>
      filteredRows.map((row, index) => ({
        ...row,
        __rowKey: tableRowKey(row, table.title, index),
      })),
    [filteredRows, table.title],
  );
  return (
    <Space direction="vertical" size={8} className="table-pane">
      <div className="table-pane-head">
        <Typography.Text type="secondary">
          {countText(filteredRows.length, table.rows.length, query)}
        </Typography.Text>
        {table.edit?.createEndpoint && onEdit ? (
          <Button type="primary" size="small" onClick={() => onEdit(table.edit as ModuleEditConfig, {}, true)}>
            Ny
          </Button>
        ) : null}
      </div>
      <Table
        rowKey="__rowKey"
        size="small"
        columns={columns}
        dataSource={tableRows}
        pagination={{ pageSize: 25, showSizeChanger: true }}
        scroll={{ x: "max-content" }}
        locale={{
          emptyText: query.trim() ? "Ingen treff for sÃ¸ket" : "Ingen rader Ã¥ vise",
        }}
      />
    </Space>
  );
}
