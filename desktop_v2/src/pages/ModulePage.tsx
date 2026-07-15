import { App as AntApp, Button, Card, Form, Modal, Space, Tabs } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { Navigate, useParams, useSearchParams } from "react-router-dom";
import {
  fetchModule,
  runModuleAction,
  submitModuleEdit,
  type JsonRecord,
  type ModuleAction,
  type ModuleEditConfig,
  type ModuleRow,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { TableSearch } from "../components/TableSearch";
import { useApiQuery } from "../hooks";
import { defaultModuleView, modulePath, MODULE_VIEWS } from "../moduleViews";
import { queryKeys } from "../queryKeys";
import { ModuleDayNavigationBar } from "./module/ModuleDayNavigationBar";
import { ModuleFilterBar } from "./module/ModuleFilterBar";
import { ModuleMetric } from "./module/ModuleMetric";
import { ModuleTablePane, tabLabel, tableSearchPlaceholder } from "./module/ModuleTablePane";
import { ControlSettingsPanel } from "./module/ControlSettingsPanel";
import { MaintenanceVisitsPanel } from "./module/MaintenanceVisitsPanel";
import { ParkingTimelinePanel } from "./module/ParkingTimelinePanel";
import { SunTimelinePanel } from "./module/SunTimelinePanel";
import { SunSessionsPanel } from "./module/SunSessionsPanel";
import { KobleReviewPanel } from "./module/KobleReviewPanel";
import { editInitialValues, fieldInput } from "./module/moduleTableUtils";
import "../styles/records.css";

const EnergyElviaPage = lazy(() => import("./EnergyElviaPage"));
const EnergySunbedsPage = lazy(() => import("./EnergySunbedsPage"));
const EnergyCircuitLoadsPage = lazy(() => import("./EnergyCircuitLoadsPage"));
const ModuleChartPanel = lazy(() => import("./module/ModuleChartPanel"));
const VentilationPage = lazy(() => import("./VentilationPage"));

const MINUTE = 60_000;
const MODULE_STALE_TIME: Record<string, number> = {
  "admin:build": 5 * MINUTE,
  "admin:datakilder": MINUTE,
  "admin:system": 5 * MINUTE,
  "energi:elvia": 5 * MINUTE,
  "energi:forbruk-per-seng": 5 * MINUTE,
  "energi:kurs-last": 5 * MINUTE,
  "energi:kurser": 5 * MINUTE,
  "energi:laster": 5 * MINUTE,
  "energi:status": 20_000,
  "energi:verktoy": 5 * MINUTE,
  "lys:hendelser": 2 * MINUTE,
  "lys:innstillinger": 5 * MINUTE,
  "omsetning:oppgjor": 5 * MINUTE,
  "omsetning:oversikt": 2 * MINUTE,
  "parkering:bilstatistikk": 5 * MINUTE,
  "parkering:kjoretoy": 5 * MINUTE,
  "parkering:omrade": 2 * MINUTE,
  "parkering:oppgjor": 5 * MINUTE,
  "parkering:oppslag": 2 * MINUTE,
  "renhold:roboter": MINUTE,
  "soling:enkeltimer": MINUTE,
  "soling:kunder": 5 * MINUTE,
  "soling:oppgjor": 5 * MINUTE,
  "soling:produkter": 5 * MINUTE,
  "soling:rom": 5 * MINUTE,
  "soling:statistikk": 5 * MINUTE,
  "vedlikehold:oversikt": MINUTE,
  "ventilasjon:hendelser": 2 * MINUTE,
  "ventilasjon:innstillinger": 5 * MINUTE,
  "ventilasjon:temp-logg": 2 * MINUTE,
  "ventilasjon:yr-logg": 5 * MINUTE,
};

function moduleStaleTime(module: string, view: string) {
  return MODULE_STALE_TIME[`${module}:${view}`] ?? 30_000;
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
    { staleTime: moduleStaleTime(module, safeView) },
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

  function setServerPage(page: number) {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("page", String(Math.max(1, page)));
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
  if (module === "energi" && safeView === "kurs-last" && data.energyCircuitLoads) {
    return (
      <Suspense fallback={<LoadingBlock />}>
        <EnergyCircuitLoadsPage data={data} />
      </Suspense>
    );
  }
  const hideModuleChrome = Boolean(data.parkingTimeline);
  const hasControlSettings = Boolean(data.controlSettings);
  const isSunSessionsView = module === "soling" && safeView === "enkeltimer";
  const isParkingSessionsView = module === "parkering" && safeView === "parkeringer";
  const kobleTableTitlesByView: Record<string, string[]> = {
    treffgrunnlag: ["Treffgrunnlag"],
    jobb: ["Jobbparametere", "Sist behandlet"],
  };
  const visibleTables =
    module === "koble"
      ? data.tables.filter((table) => (kobleTableTitlesByView[safeView] ?? []).includes(table.title))
      : data.tables;
  const isMaintenanceVisitsView = module === "vedlikehold" && safeView === "besok";
  const showStackedTables = module === "vedlikehold";
  const maintenanceVisitsTable = isMaintenanceVisitsView
    ? visibleTables.find((table) => table.title.toLowerCase().includes("lilletorget"))
    : undefined;
  const maintenanceTasksTable = isMaintenanceVisitsView
    ? visibleTables.find((table) => table.title.toLowerCase().includes("oppgaver"))
    : undefined;
  const showModuleActions = Boolean(data.actions?.length && !hideModuleChrome && !isParkingSessionsView && !(module === "koble" && safeView !== "jobb"));
  const showModuleCards = Boolean(data.cards.length && !hideModuleChrome && !hasControlSettings && !(module === "koble" && safeView !== "oversikt"));
  const editFields = editState ? (editState.create ? editState.edit.createFields ?? editState.edit.fields : editState.edit.fields) : [];
  const splitEdit = editState?.edit.layout === "split";
  const renderEditField = (field: (typeof editFields)[number]) => (
    <Form.Item
      key={field.key}
      name={field.key}
      label={field.type === "boolean" ? undefined : field.label}
      valuePropName={field.type === "boolean" ? "checked" : "value"}
      rules={field.required ? [{ required: true, message: `${field.label} må fylles ut` }] : undefined}
    >
      {fieldInput(field)}
    </Form.Item>
  );

  return (
    <Space direction="vertical" size={18} className="page-stack">
      {showModuleActions ? (
        <Card className="work-card module-actions">
          <Space>
            {(data.actions ?? []).map((action) => (
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
        <ModuleDayNavigationBar
          navigation={data.dayNavigation}
          actions={isParkingSessionsView ? (data.actions ?? []).filter((action) => action.key === "easypark-refresh") : []}
          runningAction={runningAction}
          onAction={handleAction}
          onDayChange={setTimelineDay}
        />
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
      {data.controlSettings ? (
        <ControlSettingsPanel settings={data.controlSettings} onReload={reloadModule} />
      ) : null}

      {showModuleCards ? (
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
          {module === "koble" && data.kobleReview ? <KobleReviewPanel review={data.kobleReview} view={safeView} onReload={reloadModule} /> : null}
          {data.charts?.map((chart) => <ModuleChartPanel chart={chart} key={chart.title} onDayChange={setTimelineDay} />)}

      {visibleTables.length ? (
        isMaintenanceVisitsView && maintenanceVisitsTable ? (
          <Space direction="vertical" size={12} className="module-stacked-table-area">
            <Card className="table-card module-table-card module-table-search-card">
              <TableSearch
                placeholder="Søk i besøk og oppgaver"
                value={draftQuery}
                onValueChange={setDraftQuery}
                onClear={clearSearch}
                onSearch={runSearch}
              />
            </Card>
            <MaintenanceVisitsPanel
              visitsTable={maintenanceVisitsTable}
              tasksTable={maintenanceTasksTable}
              query={query}
            />
          </Space>
        ) : showStackedTables ? (
          <Space direction="vertical" size={12} className="module-stacked-table-area">
            <Card className="table-card module-table-card module-table-search-card">
              <TableSearch
                placeholder={tableSearchPlaceholder(module, safeView)}
                value={draftQuery}
                onValueChange={setDraftQuery}
                onClear={clearSearch}
                onSearch={runSearch}
              />
            </Card>
            {visibleTables.map((table) => (
              <Card className="table-card module-table-card" key={table.title} title={tabLabel(table, query)}>
                <ModuleTablePane table={table} query={query} onEdit={openEdit} onServerPageChange={setServerPage} />
              </Card>
            ))}
          </Space>
        ) : (
          <Card className="table-card module-table-card">
            <TableSearch
              placeholder={tableSearchPlaceholder(module, safeView)}
              value={draftQuery}
              onValueChange={setDraftQuery}
              onClear={clearSearch}
              onSearch={runSearch}
            />
            <Tabs
              items={visibleTables.map((table) => ({
                key: table.title,
                label: tabLabel(table, query),
                children: <ModuleTablePane table={table} query={query} onEdit={openEdit} onServerPageChange={setServerPage} />,
              }))}
            />
          </Card>
        )
      ) : null}
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
        width={editState?.edit.width ?? (splitEdit ? 960 : undefined)}
        className={splitEdit ? "module-edit-modal module-edit-modal-split" : "module-edit-modal"}
        onOk={saveEdit}
        onCancel={() => setEditState(null)}
        destroyOnHidden
      >
        {editState ? (
          <Form form={form} layout="vertical" className={splitEdit ? "edit-form edit-form-split" : "edit-form"}>
            {splitEdit ? (
              <div className="edit-form-split-grid">
                <div className="edit-form-section edit-form-section-meta">
                  <div className="edit-form-section-title">Detaljer</div>
                  {editFields.filter((field) => field.section !== "main").map(renderEditField)}
                </div>
                <div className="edit-form-section edit-form-section-main">
                  <div className="edit-form-section-title">Notat og oppfølging</div>
                  {editFields.filter((field) => field.section === "main").map(renderEditField)}
                </div>
              </div>
            ) : (
              editFields.map(renderEditField)
            )}
          </Form>
        ) : null}
      </Modal>
    </Space>
  );
}
