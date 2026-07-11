import { Button, Space, Table, Typography } from "antd";
import { useMemo } from "react";
import type { ReactNode } from "react";

import type { ModuleEditConfig, ModuleRow, ModuleTable } from "../../api";
import { countText, filterRows, moduleColumns, tableRowKey } from "./moduleTableUtils";

function hasServerPaging(table: ModuleTable) {
  return Boolean(table.meta?.pageSize && typeof table.meta?.totalRows === "number");
}

export function tabLabel(table: ModuleTable, query: string): ReactNode {
  const serverPaged = hasServerPaging(table);
  const filteredCount = serverPaged ? table.rows.length : filterRows(table.rows, table.columns, query).length;
  const totalRows = table.meta?.totalRows;
  return (
    <span>
      {table.title}
      <span className="tab-count">
        {query.trim()
          ? `${filteredCount}/${table.rows.length}`
          : typeof totalRows === "number" && totalRows > table.rows.length
            ? `${table.rows.length}/${totalRows}`
            : table.rows.length}
      </span>
    </span>
  );
}

export function tableSearchPlaceholder(module: string, view: string): string {
  if (module === "koble") return "Søk etter SUN2, reg.nr, bil eller bruker";
  if (module === "parkering" && view === "kjoretoy") return "Søk etter reg.nr, bil, eier, område. Bruk \"nordby\" for eksakt ord.";
  return "Søk i tabellene";
}

export function ModuleTablePane({
  table,
  query,
  onEdit,
  onServerPageChange,
}: {
  table: ModuleTable;
  query: string;
  onEdit?: (edit: ModuleEditConfig, row: ModuleRow, create?: boolean) => void;
  onServerPageChange?: (page: number) => void;
}) {
  const columns = useMemo(() => moduleColumns(table, onEdit), [onEdit, table]);
  const serverPaged = hasServerPaging(table);
  const filteredRows = useMemo(
    () => (serverPaged ? table.rows : filterRows(table.rows, table.columns, query)),
    [query, serverPaged, table.columns, table.rows],
  );
  const tableRows = useMemo(
    () =>
      filteredRows.map((row, index) => ({
        ...row,
        __rowKey: tableRowKey(row, table.title, index),
      })),
    [filteredRows, table.title],
  );
  const meta = table.meta;
  const metaText =
    meta && typeof meta.totalRows === "number"
      ? `Viser ${meta.firstRow ?? 0}-${meta.lastRow ?? filteredRows.length} av ${meta.totalRows}`
      : "";
  return (
    <Space direction="vertical" size={8} className="table-pane">
      <div className="table-pane-head">
        <Typography.Text type="secondary">{metaText || countText(filteredRows.length, table.rows.length, query)}</Typography.Text>
        <Space size={6}>
          {meta && onServerPageChange ? (
            <>
              <Button size="small" disabled={!meta.hasPrevious} onClick={() => onServerPageChange(Math.max(1, (meta.page ?? 1) - 1))}>
                Forrige
              </Button>
              <Button size="small" disabled={!meta.hasMore} onClick={() => onServerPageChange((meta.page ?? 1) + 1)}>
                Neste
              </Button>
            </>
          ) : null}
          {table.edit?.createEndpoint && onEdit ? (
            <Button type="primary" size="small" onClick={() => onEdit(table.edit as ModuleEditConfig, {}, true)}>
              Ny
            </Button>
          ) : null}
        </Space>
      </div>
      <Table
        rowKey="__rowKey"
        size="small"
        columns={columns}
        dataSource={tableRows}
        pagination={meta?.disablePagination ? false : { pageSize: 25, showSizeChanger: true }}
        scroll={{ x: "max-content" }}
        locale={{
          emptyText: query.trim() ? "Ingen treff for søket" : "Ingen rader å vise",
        }}
      />
    </Space>
  );
}
