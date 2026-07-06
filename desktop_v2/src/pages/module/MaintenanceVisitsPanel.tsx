import { FileTextOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Button, Card, Empty, Input, Space, Tag } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { submitModuleEdit, type ModuleEditConfig, type ModuleRow, type ModuleTable } from "../../api";
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

const visitNoteEdit: ModuleEditConfig = {
  kind: "site-visit-note",
  title: "besoksnotat",
  idField: "id",
  endpoint: "/api/maintenance/site-visits/{id}",
  method: "PATCH",
  fields: [{ key: "notes", label: "Notat for besoket", type: "textarea", rows: 5 }],
};

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
  const queryClient = useQueryClient();
  const { message } = AntApp.useApp();
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);
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

  useEffect(() => {
    setNoteText(typeof selectedVisit?.notes === "string" ? selectedVisit.notes : "");
  }, [selectedVisit]);

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

  async function saveVisitNote() {
    if (!selectedVisit || savingNote) return;
    setSavingNote(true);
    try {
      const result = await submitModuleEdit(visitNoteEdit, selectedVisit, { notes: noteText });
      message.success(String(result.message || "Lagret"));
      queryClient.invalidateQueries({ queryKey: ["module", "vedlikehold"] });
      queryClient.invalidateQueries({ queryKey: ["maintenance", "site-visit", rowId(selectedVisit)] });
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lagring feilet");
    } finally {
      setSavingNote(false);
    }
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
                  <span className="maintenance-visit-row-main">
                    <strong>{displayValue(visit.started_at)}</strong>
                    <small>{displayValue(visit.duration)}</small>
                  </span>
                  <span className="maintenance-visit-row-meta">
                    <Tag color={visitStatusColor(visit)}>{displayValue(visit.status)}</Tag>
                    <em>{displayValue(visit.tasks_count)} oppg.</em>
                  </span>
                </button>
              );
            })
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={query.trim() ? "Ingen besøk matcher søket" : "Ingen besøk"} />
          )}
        </div>
      </Card>

      <Space direction="vertical" size={12} className="maintenance-visit-detail-column">
        <Card className="work-card maintenance-selected-visit-card">
          {selectedVisit ? (
            <Space direction="vertical" size={12} className="maintenance-selected-visit-stack">
              <div className="maintenance-selected-visit-head">
                <div>
                  <span>Valgt besøk</span>
                  <strong>{displayValue(selectedVisit.started_at)}</strong>
                </div>
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
              </div>
              <div className="maintenance-selected-visit-content">
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
                </div>
                <div className="maintenance-note-panel">
                  <div className="maintenance-note-head">
                    <span>Notat</span>
                    <Button
                      disabled={noteText === (typeof selectedVisit.notes === "string" ? selectedVisit.notes : "")}
                      icon={<SaveOutlined />}
                      loading={savingNote}
                      size="small"
                      type="primary"
                      onClick={saveVisitNote}
                    >
                      Lagre
                    </Button>
                  </div>
                  <Input.TextArea
                    value={noteText}
                    autoSize={{ minRows: 4, maxRows: 8 }}
                    placeholder="Skriv notat for besøket."
                    onChange={(event) => setNoteText(event.target.value)}
                  />
                </div>
              </div>
            </Space>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Velg et besøk i listen" />
          )}
        </Card>

        <Card
          className="table-card module-table-card maintenance-tasks-card"
          title={selectedVisit ? `Oppgaver (${selectedTasks.length})` : "Oppgaver"}
        >
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
