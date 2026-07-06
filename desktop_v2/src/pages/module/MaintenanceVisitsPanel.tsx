import { CheckCircleOutlined, EditOutlined, ExclamationCircleOutlined, FileTextOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { App as AntApp, Button, Card, Empty, Form, Input, Modal, Space, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { submitModuleEdit, type JsonRecord, type ModuleEditConfig, type ModuleRow, type ModuleTable } from "../../api";
import { displayValue, editInitialValues, fieldInput, filterRows } from "./moduleTableUtils";

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
}: {
  visitsTable: ModuleTable;
  tasksTable?: ModuleTable;
  query: string;
}) {
  const queryClient = useQueryClient();
  const { message } = AntApp.useApp();
  const [taskForm] = Form.useForm();
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [taskEditState, setTaskEditState] = useState<{ row: ModuleRow; create: boolean } | null>(null);
  const [savingTask, setSavingTask] = useState(false);
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
  const taskEdit = tasksTable?.edit;
  const taskEditFields = taskEditState && taskEdit ? (taskEditState.create ? taskEdit.createFields ?? taskEdit.fields : taskEdit.fields) : [];

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
    openTaskEditor(
      {
        site_visit_id: selectedVisit.id,
        performed_at: String(selectedVisit.ended_at ?? selectedVisit.started_at ?? "").slice(0, 16),
        presence_type: "Tilstede Sun2",
      },
      true,
    );
  }

  function openTaskEditor(row: ModuleRow, create = false) {
    if (!taskEdit) return;
    taskForm.resetFields();
    taskForm.setFieldsValue(editInitialValues(taskEdit, row, create));
    setTaskEditState({ row, create });
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

  async function saveTask() {
    if (!taskEditState || !taskEdit || savingTask) return;
    const values = (await taskForm.validateFields()) as JsonRecord;
    setSavingTask(true);
    try {
      const result = await submitModuleEdit(taskEdit, taskEditState.row, values, taskEditState.create);
      message.success(String(result.message || "Lagret"));
      setTaskEditState(null);
      queryClient.invalidateQueries({ queryKey: ["module", "vedlikehold"] });
      if (selectedVisit) {
        queryClient.invalidateQueries({ queryKey: ["maintenance", "site-visit", rowId(selectedVisit)] });
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lagring feilet");
    } finally {
      setSavingTask(false);
    }
  }

  function renderTaskEditField(field: (typeof taskEditFields)[number]) {
    const compactRows: Record<string, number> = {
      summary: 5,
      follow_up_text: 3,
    };
    const inputField = field.type === "textarea" && compactRows[field.key] ? { ...field, rows: compactRows[field.key] } : field;
    const wideField = field.type === "textarea" || field.type === "tags" || field.key === "target_name";
    return (
      <Form.Item
        className={wideField ? "maintenance-task-edit-field-wide" : undefined}
        key={field.key}
        name={field.key}
        label={field.type === "boolean" ? undefined : field.label}
        valuePropName={field.type === "boolean" ? "checked" : "value"}
        rules={field.required ? [{ required: true, message: `${field.label} må fylles ut` }] : undefined}
      >
        {fieldInput(inputField)}
      </Form.Item>
    );
  }

  return (
    <>
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

          <Card className="table-card module-table-card maintenance-tasks-card">
            <div className="maintenance-tasks-head">
              <div>
                <span>Oppgaver</span>
                <strong>{selectedTasks.length}</strong>
              </div>
              <Button
                disabled={!selectedVisit || !tasksTable?.edit?.createEndpoint}
                icon={<PlusOutlined />}
                size="small"
                type="primary"
                onClick={createTaskForSelectedVisit}
              >
                Ny
              </Button>
            </div>
            {tasksTable ? (
              selectedTasks.length ? (
                <div className="maintenance-task-list">
                  {selectedTasks.map((task) => (
                    <button
                      className="maintenance-task-row"
                      key={rowId(task)}
                      type="button"
                      onClick={() => openTaskEditor(task)}
                    >
                      <span className="maintenance-task-row-icon">
                        {task.follow_up_needed ? <ExclamationCircleOutlined /> : <CheckCircleOutlined />}
                      </span>
                      <span className="maintenance-task-row-main">
                        <span className="maintenance-task-row-title">{displayValue(task.summary)}</span>
                        <span className="maintenance-task-row-sub">
                          {displayValue(task.performed_at)} · {displayValue(task.target_type)} · {displayValue(task.target_name)}
                        </span>
                        {task.follow_up_needed && task.follow_up_text ? (
                          <span className="maintenance-task-follow-up">{displayValue(task.follow_up_text)}</span>
                        ) : null}
                      </span>
                      <span className="maintenance-task-row-meta">
                        <Tag>{displayValue(task.status)}</Tag>
                        <small>{displayValue(task.action_type)}</small>
                        <EditOutlined />
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen oppgaver på valgt besøk">
                  <Button
                    disabled={!selectedVisit || !tasksTable.edit?.createEndpoint}
                    icon={<PlusOutlined />}
                    type="primary"
                    onClick={createTaskForSelectedVisit}
                  >
                    Legg til oppgave
                  </Button>
                </Empty>
              )
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen oppgavetabell" />
            )}
          </Card>
        </Space>
      </div>
      <Modal
        className="maintenance-task-modal"
        title={taskEditState?.create ? "Ny vedlikeholdsoppgave" : "Rediger vedlikeholdsoppgave"}
        open={Boolean(taskEditState)}
        okText="Lagre"
        cancelText="Avbryt"
        confirmLoading={savingTask}
        width={900}
        destroyOnHidden
        onCancel={() => setTaskEditState(null)}
        onOk={saveTask}
      >
        {taskEditState && taskEdit ? (
          <Form form={taskForm} layout="vertical" className="maintenance-task-edit-form">
            <div className="maintenance-task-edit-grid">
              <div className="maintenance-task-edit-section maintenance-task-edit-section-meta">
                <Typography.Text className="maintenance-task-edit-title">Detaljer</Typography.Text>
                <div className="maintenance-task-edit-meta-grid">
                  {taskEditFields.filter((field) => field.section !== "main").map(renderTaskEditField)}
                </div>
              </div>
              <div className="maintenance-task-edit-section maintenance-task-edit-section-main">
                <Typography.Text className="maintenance-task-edit-title">Notat og oppfølging</Typography.Text>
                {taskEditFields.filter((field) => field.section === "main").map(renderTaskEditField)}
              </div>
            </div>
          </Form>
        ) : null}
      </Modal>
    </>
  );
}
