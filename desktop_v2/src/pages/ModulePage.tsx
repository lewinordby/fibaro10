import { CalendarOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Card, Form, Input, Modal, Space, Table, Tabs, Typography } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useParams, useSearchParams } from "react-router-dom";
import {
  fetchModule,
  runModuleAction,
  submitModuleEdit,
  type JsonRecord,
  type ModuleAction,
  type ModuleDayNavigation,
  type ModuleEditConfig,
  type ModuleRow,
  type ModuleTable,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PeriodNavigator } from "../components/PeriodNavigator";
import { TableSearch } from "../components/TableSearch";
import { useApiQuery } from "../hooks";
import { defaultModuleView, modulePath, MODULE_VIEWS } from "../moduleViews";
import { queryKeys } from "../queryKeys";
import { ModuleFilterBar } from "./module/ModuleFilterBar";
import { ModuleMetric } from "./module/ModuleMetric";
import { ParkingTimelinePanel } from "./module/ParkingTimelinePanel";
import { SunTimelinePanel } from "./module/SunTimelinePanel";
import { SunSessionsPanel } from "./module/SunSessionsPanel";
import { countText, editInitialValues, fieldInput, filterRows, moduleColumns, tableRowKey } from "./module/moduleTableUtils";

const EnergyElviaPage = lazy(() => import("./EnergyElviaPage"));
const EnergySunbedsPage = lazy(() => import("./EnergySunbedsPage"));
const ModuleChartPanel = lazy(() => import("./module/ModuleChartPanel"));
const VentilationPage = lazy(() => import("./VentilationPage"));

function ModuleDayNavigationBar({
  navigation,
  onDayChange,
}: {
  navigation: ModuleDayNavigation;
  onDayChange: (day: string) => void;
}) {
  return (
    <Card className="work-card module-day-nav-card">
      <div className="module-day-nav-title">
        <Typography.Text type="secondary">Dato</Typography.Text>
        <Typography.Text strong>{navigation.selectedDayLabel}</Typography.Text>
      </div>
      <PeriodNavigator
        className="module-day-nav-actions"
        previousLabel="Forrige dag"
        nextLabel="Neste dag"
        onPrevious={() => onDayChange(navigation.prevDay)}
        onNext={() => onDayChange(navigation.nextDay)}
        middle={
          <Button size="small" onClick={() => onDayChange("")}>
            I dag
          </Button>
        }
        extra={
          <Input
            aria-label="Dato"
            className="module-day-nav-date"
            prefix={<CalendarOutlined />}
            size="small"
            type="date"
            value={navigation.selectedDay}
            onChange={(event) => onDayChange(event.target.value)}
          />
        }
      />
    </Card>
  );
}

function tabLabel(table: ModuleTable, query: string): ReactNode {
  const filteredCount = filterRows(table.rows, table.columns, query).length;
  return (
    <span>
      {table.title}
      <span className="tab-count">{query.trim() ? `${filteredCount}/${table.rows.length}` : table.rows.length}</span>
    </span>
  );
}

function tableSearchPlaceholder(module: string, view: string): string {
  if (module === "parkering" && view === "kjoretoy") return "Søk etter reg.nr, bil, eier, område. Bruk \"nordby\" for eksakt ord.";
  return "Søk i tabellene";
}

function ModuleTablePane({
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
          emptyText: query.trim() ? "Ingen treff for søket" : "Ingen rader å vise",
        }}
      />
    </Space>
  );
}

export default function ModulePage({ module }: { module: string }) {
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { message, modal } = AntApp.useApp();
  const [form] = Form.useForm();
  const [query, setQuery] = useState("");
  const [draftQuery, setDraftQuery] = useState("");
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [editState, setEditState] = useState<{ edit: ModuleEditConfig; row: ModuleRow; create: boolean } | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const view = params.view ?? defaultModuleView(module);
  const viewItems = MODULE_VIEWS[module] ?? [];
  const isKnownView = !viewItems.length || viewItems.some((item) => item.key === view);
  const safeView = isKnownView ? view : defaultModuleView(module);
  const serverQuery = module === "parkering" && safeView === "kjoretoy" ? query : "";
  const filterKey = searchParams.toString();
  const timelineDay =
    (module === "soling" && safeView === "dagslinje") ||
    (module === "parkering" && safeView === "dagslinje") ||
    (module === "ventilasjon" && safeView === "dagslogg")
      ? searchParams.get("day") ?? ""
      : "";
  const moduleQueryKey = queryKeys.module(module, safeView, serverQuery, timelineDay || "", filterKey);
  const { data, loading, error } = useApiQuery(
    moduleQueryKey,
    () => fetchModule(module, safeView, serverQuery, timelineDay || undefined, searchParams),
  );

  if (!isKnownView) return <Navigate to={modulePath(module)} replace />;

  function reloadModule() {
    return queryClient.invalidateQueries({ queryKey: moduleQueryKey });
  }

  function runSearch(value = draftQuery) {
    setQuery(value.trim());
  }

  function clearSearch() {
    setDraftQuery("");
    setQuery("");
  }

  function setTimelineDay(day: string) {
    const nextParams = new URLSearchParams(searchParams);
    if (day) nextParams.set("day", day);
    else nextParams.delete("day");
    setSearchParams(nextParams);
  }

  function applyModuleFilters(values: Record<string, string>) {
    const nextParams = new URLSearchParams(searchParams);
    Object.entries(values).forEach(([key, value]) => {
      const trimmed = value.trim();
      if (trimmed) nextParams.set(key, trimmed);
      else nextParams.delete(key);
    });
    setSearchParams(nextParams);
  }

  function clearModuleFilters(keys: string[]) {
    const nextParams = new URLSearchParams(searchParams);
    keys.forEach((key) => nextParams.delete(key));
    setSearchParams(nextParams);
  }

  function openEdit(edit: ModuleEditConfig, row: ModuleRow, create = false) {
    form.resetFields();
    form.setFieldsValue(editInitialValues(edit, row, create));
    setEditState({ edit, row, create });
  }

  async function saveEdit() {
    if (!editState || savingEdit) return;
    const values = (await form.validateFields()) as JsonRecord;
    setSavingEdit(true);
    try {
      const result = await submitModuleEdit(editState.edit, editState.row, values, editState.create);
      message.success(String(result.message || "Lagret"));
      setEditState(null);
      await reloadModule();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lagring feilet");
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleAction(action: ModuleAction) {
    if (runningAction) return;
    const runAction = async () => {
      setRunningAction(action.key);
      try {
        const result = await runModuleAction(action);
        message.success(String(result.message || "Handling utført"));
        await reloadModule();
      } catch (err) {
        message.error(err instanceof Error ? err.message : "Handling feilet");
      } finally {
        setRunningAction(null);
      }
    };

    if (action.confirm) {
      modal.confirm({
        title: action.label,
        content: action.confirm,
        okText: "Kjør",
        cancelText: "Avbryt",
        onOk: runAction,
      });
      return;
    }
    await runAction();
  }

  if (loading) return <LoadingBlock />;
  if (error || !data) return <ErrorBlock error={error} />;
  if (module === "ventilasjon" && data.ventilation) {
    return (
      <Suspense fallback={<LoadingBlock />}>
        <VentilationPage data={data} view={safeView} onReload={reloadModule} />
      </Suspense>
    );
  }
  if (module === "energi" && safeView === "elvia" && data.energyElvia) {
    return (
      <Suspense fallback={<LoadingBlock />}>
        <EnergyElviaPage data={data} onReload={reloadModule} />
      </Suspense>
    );
  }
  if (module === "energi" && safeView === "forbruk-per-seng" && data.energySunbeds) {
    return (
      <Suspense fallback={<LoadingBlock />}>
        <Space direction="vertical" size={14} className="page-stack">
          {data.filters?.length ? (
            <ModuleFilterBar
              filters={data.filters}
              key={`${module}-${safeView}-${filterKey}`}
              onApply={applyModuleFilters}
              onClear={clearModuleFilters}
            />
          ) : null}
          <EnergySunbedsPage data={data} />
        </Space>
      </Suspense>
    );
  }
  const hideModuleChrome = Boolean(data.parkingTimeline);
  const isSunSessionsView = module === "soling" && safeView === "enkeltimer";

  return (
    <Space direction="vertical" size={18} className="page-stack">
      {data.actions?.length && !hideModuleChrome ? (
        <Card className="work-card module-actions">
          <Space>
            {data.actions.map((action) => (
              <Button
                key={action.key}
                type={action.tone === "primary" ? "primary" : "default"}
                loading={runningAction === action.key}
                disabled={Boolean(runningAction && runningAction !== action.key)}
                onClick={() => handleAction(action)}
              >
                {action.label}
              </Button>
            ))}
          </Space>
        </Card>
      ) : null}

      {data.dayNavigation && !hideModuleChrome ? (
        <ModuleDayNavigationBar navigation={data.dayNavigation} onDayChange={setTimelineDay} />
      ) : null}

      {data.filters?.length ? (
        <ModuleFilterBar
          filters={data.filters}
          key={`${module}-${safeView}-${filterKey}`}
          onApply={applyModuleFilters}
          onClear={clearModuleFilters}
        />
      ) : null}

      {isSunSessionsView ? (
        <SunSessionsPanel
          table={data.tables[0]}
          query={query}
          draftQuery={draftQuery}
          onSearch={runSearch}
          onClear={clearSearch}
          onDraftChange={setDraftQuery}
          onImageChanged={reloadModule}
        />
      ) : (
        <>
      {data.cards.length && !hideModuleChrome ? (
        <div className="metric-grid primary-grid">
          {data.cards.map((card) => (
            <ModuleMetric card={card} key={card.title} module={module} view={safeView} />
          ))}
        </div>
      ) : null}

      {data.sunTimeline ? (
        <SunTimelinePanel timeline={data.sunTimeline} onDayChange={setTimelineDay} />
      ) : data.parkingTimeline ? (
        <ParkingTimelinePanel timeline={data.parkingTimeline} onDayChange={setTimelineDay} />
      ) : (
        <>
          {data.charts?.map((chart) => <ModuleChartPanel chart={chart} key={chart.title} onDayChange={setTimelineDay} />)}

      <Card className="table-card module-table-card">
        <TableSearch
          placeholder={tableSearchPlaceholder(module, safeView)}
          value={draftQuery}
          onValueChange={setDraftQuery}
          onClear={clearSearch}
          onSearch={runSearch}
        />
        <Tabs
          items={data.tables.map((table) => ({
            key: table.title,
            label: tabLabel(table, query),
            children: <ModuleTablePane table={table} query={query} onEdit={openEdit} />,
          }))}
        />
      </Card>
        </>
      )}
        </>
      )}

      <Modal
        title={
          editState
            ? `${editState.create ? "Ny" : "Rediger"} ${editState.edit.title.toLowerCase()}`
            : "Rediger"
        }
        open={Boolean(editState)}
        okText="Lagre"
        cancelText="Avbryt"
        confirmLoading={savingEdit}
        onOk={saveEdit}
        onCancel={() => setEditState(null)}
        destroyOnHidden
      >
        {editState ? (
          <Form form={form} layout="vertical" className="edit-form">
            {(editState.create ? editState.edit.createFields ?? editState.edit.fields : editState.edit.fields).map((field) => (
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
          </Form>
        ) : null}
      </Modal>
    </Space>
  );
}
