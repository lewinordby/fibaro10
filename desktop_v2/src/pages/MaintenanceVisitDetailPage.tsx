import { ArrowLeftOutlined, EditOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Card, Collapse, Form, Input, Modal, Space, Typography } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  fetchMaintenanceSiteVisitDetail,
  submitModuleEdit,
  type JsonRecord,
  type ModuleEditConfig,
  type ModuleRow,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import { ModuleMetric } from "./module/ModuleMetric";
import { ModuleTablePane } from "./module/ModuleTablePane";
import { displayValue, editInitialValues, fieldInput } from "./module/moduleTableUtils";
import "../styles/records.css";
import "../styles/maintenance.css";

export default function MaintenanceVisitDetailPage() {
  const { visitId = "" } = useParams();
  const queryClient = useQueryClient();
  const { message } = AntApp.useApp();
  const [taskForm] = Form.useForm();
  const [notes, setNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [taskEditState, setTaskEditState] = useState<{ edit: ModuleEditConfig; row: ModuleRow; create: boolean } | null>(null);
  const [savingTask, setSavingTask] = useState(false);
  const queryKey = queryKeys.maintenanceSiteVisit(visitId);
  const { data, loading, error } = useApiQuery(queryKey, () => fetchMaintenanceSiteVisitDetail(visitId), {
    enabled: Boolean(visitId),
    staleTime: 60_000,
  });

  useEffect(() => {
    setNotes(typeof data?.visit.notes === "string" ? data.visit.notes : "");
  }, [data?.visit.notes]);

  const rawText = useMemo(() => JSON.stringify(data?.raw ?? {}, null, 2), [data?.raw]);

  function reload() {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ["module", "vedlikehold"] });
  }

  function openTaskEdit(edit: ModuleEditConfig, row: ModuleRow, create = false) {
    taskForm.resetFields();
    taskForm.setFieldsValue(editInitialValues(edit, row, create));
    setTaskEditState({ edit, row, create });
  }

  function openCreateTask() {
    if (!data) return;
    openTaskEdit(
      data.taskEdit,
      {
        site_visit_id: data.visit.id,
        performed_at: String(data.visit.ended_at ?? data.visit.started_at ?? "").slice(0, 16),
        presence_type: "Tilstede Sun2",
      },
      true,
    );
  }

  async function saveNotes() {
    if (!data || savingNotes) return;
    setSavingNotes(true);
    try {
      const result = await submitModuleEdit(data.visitEdit, data.visit, { notes });
      message.success(String(result.message || "Lagret"));
      reload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lagring feilet");
    } finally {
      setSavingNotes(false);
    }
  }

  async function saveTask() {
    if (!taskEditState || savingTask) return;
    const values = (await taskForm.validateFields()) as JsonRecord;
    setSavingTask(true);
    try {
      const result = await submitModuleEdit(taskEditState.edit, taskEditState.row, values, taskEditState.create);
      message.success(String(result.message || "Lagret"));
      setTaskEditState(null);
      reload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lagring feilet");
    } finally {
      setSavingTask(false);
    }
  }

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;

  const editFields = taskEditState ? (taskEditState.create ? taskEditState.edit.createFields ?? taskEditState.edit.fields : taskEditState.edit.fields) : [];

  return (
    <Space direction="vertical" size={16} className="page-stack maintenance-visit-detail">
      <div className="visit-detail-top">
        <Space direction="vertical" size={2}>
          <Link to="/vedlikehold/besok" className="back-link">
            <ArrowLeftOutlined /> Til besøk
          </Link>
          <Typography.Title level={2}>{data.title}</Typography.Title>
          <Typography.Text type="secondary">{data.subtitle}</Typography.Text>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateTask}>
          Ny oppgave
        </Button>
      </div>

      <div className="visit-detail-card-grid">
        {data.cards.map((card) => (
          <ModuleMetric key={card.title} card={{ ...card, href: "/vedlikehold/besok" }} module="vedlikehold" view="besok" />
        ))}
      </div>

      <div className="visit-detail-layout">
        <Space direction="vertical" size={12}>
          <Card className="work-card visit-detail-note-card">
            <div className="visit-card-head">
              <Typography.Title level={4}>Besøksnotat</Typography.Title>
              <Button type="primary" icon={<SaveOutlined />} loading={savingNotes} onClick={saveNotes}>
                Lagre
              </Button>
            </div>
            <Input.TextArea
              value={notes}
              rows={8}
              placeholder="Skriv mer om besøket, hva som ble observert, eller hva som bør følges opp."
              onChange={(event) => setNotes(event.target.value)}
            />
          </Card>

          <Card className="work-card">
            <Typography.Title level={4}>Detaljer</Typography.Title>
            <div className="visit-field-grid">
              {data.fields.map((field) => (
                <div className="visit-field" key={field.label}>
                  <span>{field.label}</span>
                  <strong>{displayValue(field.value)}</strong>
                </div>
              ))}
            </div>
          </Card>
        </Space>

        <Space direction="vertical" size={12}>
          <Card
            className="work-card module-table-card"
            title="Oppgaver på dette besøket"
            extra={
              <Button size="small" icon={<PlusOutlined />} onClick={openCreateTask}>
                Ny
              </Button>
            }
          >
            <ModuleTablePane table={data.taskTable} query="" onEdit={openTaskEdit} />
          </Card>

          <Collapse
            items={[
              {
                key: "raw",
                label: "Rådata fra OwnTracks",
                children: <Input.TextArea value={rawText} rows={10} readOnly />,
              },
            ]}
          />
        </Space>
      </div>

      <Modal
        className={taskEditState?.edit.layout === "split" ? "module-edit-modal-split" : undefined}
        title={`${taskEditState?.create ? "Ny" : "Rediger"} ${taskEditState?.edit.title ?? "oppgave"}`}
        open={Boolean(taskEditState)}
        onCancel={() => setTaskEditState(null)}
        onOk={saveTask}
        confirmLoading={savingTask}
        okText="Lagre"
        cancelText="Avbryt"
        width={taskEditState?.edit.width ?? 720}
        destroyOnHidden
      >
        <Form form={taskForm} layout="vertical" className={taskEditState?.edit.layout === "split" ? "edit-form edit-form-split" : "edit-form"}>
          {taskEditState?.edit.layout === "split" ? (
            <div className="edit-form-split-grid">
              <div className="edit-form-section">
                <div className="edit-form-section-title">Metadata</div>
                {editFields.filter((field) => field.section !== "main").map((field) => (
                  <Form.Item
                    key={field.key}
                    name={field.key}
                    label={field.type === "boolean" ? undefined : field.label}
                    valuePropName={field.type === "boolean" ? "checked" : "value"}
                    rules={field.required ? [{ required: true, message: `${field.label} må fylles ut` }] : undefined}
                  >
                    {fieldInput(field)}
                  </Form.Item>
                ))}
              </div>
              <div className="edit-form-section edit-form-section-main">
                <div className="edit-form-section-title">Innhold</div>
                {editFields.filter((field) => field.section === "main").map((field) => (
                  <Form.Item
                    key={field.key}
                    name={field.key}
                    label={field.type === "boolean" ? undefined : field.label}
                    valuePropName={field.type === "boolean" ? "checked" : "value"}
                    rules={field.required ? [{ required: true, message: `${field.label} må fylles ut` }] : undefined}
                  >
                    {fieldInput(field)}
                  </Form.Item>
                ))}
              </div>
            </div>
          ) : (
            editFields.map((field) => (
              <Form.Item
                key={field.key}
                name={field.key}
                label={field.type === "boolean" ? undefined : field.label}
                valuePropName={field.type === "boolean" ? "checked" : "value"}
                rules={field.required ? [{ required: true, message: `${field.label} må fylles ut` }] : undefined}
              >
                {fieldInput(field)}
              </Form.Item>
            ))
          )}
        </Form>
      </Modal>
    </Space>
  );
}
