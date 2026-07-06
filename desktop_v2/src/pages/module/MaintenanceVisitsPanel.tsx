import { FileTextOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Card, Empty, Space, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { ModuleEditConfig, ModuleRow, ModuleTable } from "../../api";
import { displayValue, filterRows } from "./moduleTableUtils";
import { ModuleTablePane } from "./ModuleTablePane";

function rowId(row: ModuleRow): string {
  return String(row.id ?? "");
}

function visitPath(row: ModuleRow): string {
  const path = row.path;
  if (typeof path === "string" && path) return path;
  return `/vedlikehold/besok/${encodeURIComponent(rowId(row))}`;
}

function visitStatusColor(row: ModuleRow): string {
  const status = String(row.status ?? "").toLowerCase();
  if (status.includes("aktiv") || status.includes("open")) return "green";
  return "default";
}

function taskMatchesVisit(row: ModuleRow, visit: ModuleRow | null): boolean {
  if (!visit) return false;
  const visitId = rowId(visit);
  return String(row.site_visit_id ?? "") === visitId;
}

function taskTableForVisit(table: ModuleTable, rows: ModuleRow[]): ModuleTable {
  const edit = table.edit ? { ...table.edit, createEndpoint: undefined } : undefined;
  return { ...table, rows, edit };
}

export function MaintenanceVisitsPanel({
  visitsTable,
  tasksTable,
  query,
  onEdit,
}: {
  visitsTable: ModuleTable;
  tasksTable?: ModuleTable;
  query: string;
  onEdit: (edit: ModuleEditConfig, row: ModuleRow, create?: boolean) => void;
}) {
  const matchingTaskVisitIds = useMemo(() => {
    if (!query.trim() || !tasksTable) return new Set<string>();
    return new Set(filterRows(tasksTable.rows, tasksTable.columns, query).map((row) => String(row.site_visit_id ?? "")));
  }, [query, tasksTable]);
  const visits = useMemo(() => {
    const directMatches = filterRows(visitsTable.rows, visitsTable.columns, query);
    if (!query.trim() || !matchingTaskVisitIds.size) return directMatches;
    const directIds = new Set(directMatches.map(rowId));
    return visitsTable.rows.filter((row) => directIds.has(rowId(row)) || matchingTaskVisitIds.has(rowId(row)));
  }, [matchingTaskVisitIds, query, visitsTable]);
  const [selectedVisitId, setSelectedVisitId] = useState(() => rowId(visits[0] ?? {}));
  const selectedVisit = visits.find((row) => rowId(row) === selectedVisitId) ?? visits[0] ?? null;
  const selectedTasks = useMemo(() => {
    if (!tasksTable) return [];
    const rows = tasksTable.rows.filter((row) => taskMatchesVisit(row, selectedVisit));
    if (!query.trim()) return rows;
    const matches = filterRows(rows, tasksTable.columns, query);
    return matches.length ? matches : rows;
  }, [query, selectedVisit, tasksTable]);
  const selectedTaskTable = tasksTable ? taskTableForVisit(tasksTable, selectedTasks) : null;

  useEffect(() => {
    if (!visits.length) {
      setSelectedVisitId("");
      return;
    }
    if (!visits.some((row) => rowId(row) === selectedVisitId)) {
      setSelectedVisitId(rowId(visits[0]));
    }
  }, [selectedVisitId, visits]);

  function createTaskForSelectedVisit() {
    if (!selectedVisit || !tasksTable?.edit?.createEndpoint) return;
    onEdit(
      tasksTable.edit,
      {
        site_visit_id: selectedVisit.id,
        performed_at: String(selectedVisit.ended_at ?? selectedVisit.started_at ?? "").slice(0, 16),
        presence_type: "Tilstede Sun2",
      },
      true,
    );
  }

  return (
    <div className="maintenance-visits-master-detail">
      <Card className="table-card module-table-card maintenance-visit-list-card" title="Besøk">
        <div className="maintenance-visit-list">
          {visits.length ? (
            visits.map((visit) => {
              const active = rowId(visit) === rowId(selectedVisit ?? {});
              return (
                <button
                  className={`maintenance-visit-row ${active ? "active" : ""}`}
                  key={rowId(visit)}
                  type="button"
                  onClick={() => setSelectedVisitId(rowId(visit))}
                >
                  <span>
                    <strong>{displayValue(visit.started_at)}</strong>
                    <small>{displayValue(visit.duration)} · {displayValue(visit.tasks_count)} oppgaver</small>
                  </span>
                  <Tag color={visitStatusColor(visit)}>{displayValue(visit.status)}</Tag>
                </button>
              );
            })
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={query.trim() ? "Ingen besøk matcher søket" : "Ingen besøk"} />
          )}
        </div>
      </Card>

      <Space direction="vertical" size={12} className="maintenance-visit-detail-column">
        <Card
          className="work-card maintenance-selected-visit-card"
          title={selectedVisit ? `Valgt besøk ${displayValue(selectedVisit.started_at)}` : "Velg besøk"}
          extra={
            selectedVisit ? (
              <Space size={8}>
                <Link to={visitPath(selectedVisit)}>
                  <Button icon={<FileTextOutlined />} size="small">
                    Detaljer
                  </Button>
                </Link>
                <Button
                  disabled={!tasksTable?.edit?.createEndpoint}
                  icon={<PlusOutlined />}
                  size="small"
                  type="primary"
                  onClick={createTaskForSelectedVisit}
                >
                  Ny oppgave
                </Button>
              </Space>
            ) : null
          }
        >
          {selectedVisit ? (
            <div className="maintenance-selected-visit-summary">
              <div>
                <span>Kom</span>
                <strong>{displayValue(selectedVisit.started_at)}</strong>
              </div>
              <div>
                <span>Dro</span>
                <strong>{displayValue(selectedVisit.ended_at)}</strong>
              </div>
              <div>
                <span>Varighet</span>
                <strong>{displayValue(selectedVisit.duration)}</strong>
              </div>
              <div>
                <span>Oppgaver</span>
                <strong>{displayValue(selectedVisit.tasks_count)}</strong>
              </div>
              <div className="wide">
                <span>Notat</span>
                <Typography.Text>{displayValue(selectedVisit.notes)}</Typography.Text>
              </div>
            </div>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Velg et besøk i listen" />
          )}
        </Card>

        <Card className="table-card module-table-card" title={selectedVisit ? "Oppgaver for valgt besøk" : "Oppgaver"}>
          {selectedTaskTable ? (
            <ModuleTablePane table={selectedTaskTable} query="" onEdit={onEdit} />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen oppgavetabell" />
          )}
        </Card>
      </Space>
    </div>
  );
}
