import { CalendarOutlined } from "@ant-design/icons";
import { App as AntApp, Button, Card, Form, Input, Modal, Space, Spin, Table, Tabs, Tag, Typography } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useParams, useSearchParams } from "react-router-dom";
import {
  fetchModule,
  fetchSunSessionImageBrowser,
  runModuleAction,
  selectSunSessionImage,
  submitModuleEdit,
  type JsonRecord,
  type ModuleAction,
  type ModuleDayNavigation,
  type ModuleEditConfig,
  type ModuleRow,
  type ModuleTable,
  type SunSessionImageBrowser,
  type SunSessionSavedImage,
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
import { countText, displayValue, editInitialValues, fieldInput, filterRows, moduleColumns, tableRowKey } from "./module/moduleTableUtils";

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

function rowString(row: ModuleRow, key: string): string {
  const value = row[key];
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function sessionImageUrl(row: ModuleRow): string {
  const url = rowString(row, "image_url");
  if (!url) return "";
  const version = rowString(row, "image_captured_at") || rowString(row, "id");
  return version ? `${url}?v=${encodeURIComponent(version)}` : url;
}

function rowSavedImages(row: ModuleRow): SunSessionSavedImage[] {
  return Array.isArray(row.session_images) ? (row.session_images as SunSessionSavedImage[]) : [];
}

function SunSessionDetails({ row, onImageChanged }: { row: ModuleRow; onImageChanged: () => void }) {
  const { message } = AntApp.useApp();
  const imageUrl = sessionImageUrl(row);
  const hasImage = row.has_image === true && Boolean(imageUrl);
  const sessionId = Number(row.id);
  const canBrowseImages = Number.isFinite(sessionId) && sessionId > 0;
  const [browserOpen, setBrowserOpen] = useState(false);
  const [browserLoading, setBrowserLoading] = useState(false);
  const [savingImage, setSavingImage] = useState(false);
  const [settingPrimarySnapshotId, setSettingPrimarySnapshotId] = useState<string | null>(null);
  const [browser, setBrowser] = useState<SunSessionImageBrowser | null>(null);
  const [inlineArchiveBrowser, setInlineArchiveBrowser] = useState<SunSessionImageBrowser | null>(null);
  const [inlineArchiveLoading, setInlineArchiveLoading] = useState(false);
  const [selectedInlineImageId, setSelectedInlineImageId] = useState<number | null>(null);
  const inlineImages = rowSavedImages(row);
  const defaultInlineIndex = Math.max(0, inlineImages.findIndex((image) => image.isPrimary));
  const selectedInlineIndex = inlineImages.findIndex((image) => image.id === selectedInlineImageId);
  const activeInlineIndex = selectedInlineIndex >= 0 ? selectedInlineIndex : defaultInlineIndex;
  const activeInlineImage = inlineImages[activeInlineIndex] ?? null;
  const activeArchiveSnapshot = inlineArchiveBrowser?.current ?? null;
  const activeSnapshotId = activeArchiveSnapshot?.id || activeInlineImage?.snapshotId || "";
  const activeImageUrl = activeArchiveSnapshot
    ? `${activeArchiveSnapshot.imageUrl}?v=${encodeURIComponent(activeArchiveSnapshot.id)}`
    : activeInlineImage
      ? `${activeInlineImage.imageUrl}?v=${encodeURIComponent(activeInlineImage.id)}`
      : "";
  const activeImageLabel = activeArchiveSnapshot?.label || activeInlineImage?.label || "";
  const activeImagePrefix = activeArchiveSnapshot ? "Arkiv" : activeInlineImage ? `${activeInlineIndex + 1} av ${inlineImages.length}` : "";
  const activeImageOffset = activeArchiveSnapshot ? "Arkivbilde" : activeInlineImage?.offsetLabel || "";
  const activeImageIsPrimary = Boolean(activeArchiveSnapshot?.isLinked || activeInlineImage?.isPrimary);
  const canMoveInlinePrevious = activeArchiveSnapshot
    ? Boolean(inlineArchiveBrowser?.canPrevious)
    : Boolean(activeInlineImage && (activeInlineIndex > 0 || activeInlineImage.snapshotId));
  const canMoveInlineNext = activeArchiveSnapshot
    ? Boolean(inlineArchiveBrowser?.canNext)
    : Boolean(activeInlineImage && (activeInlineIndex < inlineImages.length - 1 || activeInlineImage.snapshotId));
  const fields: Array<[string, unknown]> = [
    ["Start", row.started_at],
    ["Slutt", row.ended_at],
    ["Rom", row.room_label || row.room || row.room_id],
    ["Varighet", row.duration_minutes ? `${displayValue(row.duration_minutes)} min` : ""],
    ["Betalt", row.paid_amount_kr ? `${displayValue(row.paid_amount_kr)} kr` : ""],
    ["Bruker", row.user_name || row.sun2_user_id],
    ["Betaling", row.payment_method],
    ["Kundetype", row.customer_type],
    ["Status", row.status],
    ["Bildetid", row.image_captured_at],
    ["Bilder", row.image_count ? `${displayValue(row.image_count)} lagret` : ""],
    ["Avvik", row.image_delta_seconds !== null && row.image_delta_seconds !== undefined ? `${displayValue(row.image_delta_seconds)} sek` : ""],
  ];

  useEffect(() => {
    setInlineArchiveBrowser(null);
    setSelectedInlineImageId(null);
  }, [row.id, row.image_captured_at, row.image_count]);

  async function openBrowser(snapshotId?: string | null) {
    if (!canBrowseImages) {
      message.error("Mangler intern soltime-ID.");
      return;
    }
    setBrowserOpen(true);
    setBrowserLoading(true);
    try {
      const nextBrowser = await fetchSunSessionImageBrowser(sessionId, snapshotId);
      setBrowser(nextBrowser);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke hente bildearkivet");
    } finally {
      setBrowserLoading(false);
    }
  }

  async function useCurrentImage() {
    if (!canBrowseImages || !browser?.current) return;
    setSavingImage(true);
    try {
      const nextBrowser = await selectSunSessionImage(sessionId, browser.current.id);
      message.success("Bildepakken er lagret");
      setBrowser(nextBrowser);
      onImageChanged();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke lagre bildepakken");
    } finally {
      setSavingImage(false);
    }
  }

  async function saveInlineSnapshotAsPrimary(snapshotId: string) {
    if (!canBrowseImages || !snapshotId || activeImageIsPrimary || settingPrimarySnapshotId) return;
    setSettingPrimarySnapshotId(snapshotId);
    try {
      const nextBrowser = await selectSunSessionImage(sessionId, snapshotId);
      message.success("Ny bildepakke er lagret");
      setInlineArchiveBrowser(nextBrowser);
      setSelectedInlineImageId(null);
      onImageChanged();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke lagre ny bildepakke");
    } finally {
      setSettingPrimarySnapshotId(null);
    }
  }

  async function showInlineArchiveSnapshot(snapshotId: string) {
    if (!canBrowseImages || !snapshotId) return;
    setInlineArchiveLoading(true);
    try {
      const nextBrowser = await fetchSunSessionImageBrowser(sessionId, snapshotId);
      setInlineArchiveBrowser(nextBrowser);
      setSelectedInlineImageId(null);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke hente bildearkivet");
    } finally {
      setInlineArchiveLoading(false);
    }
  }

  async function moveFromSavedImageToArchive(snapshotId: string, delta: number) {
    if (!canBrowseImages || !snapshotId) return;
    setInlineArchiveLoading(true);
    try {
      const referenceBrowser = await fetchSunSessionImageBrowser(sessionId, snapshotId);
      const nextSnapshotId = delta < 0 ? referenceBrowser.previousSnapshotId : referenceBrowser.nextSnapshotId;
      if (!nextSnapshotId) {
        message.info(delta < 0 ? "Ingen eldre bilder i arkivet." : "Ingen nyere bilder i arkivet.");
        return;
      }
      const nextBrowser = await fetchSunSessionImageBrowser(sessionId, nextSnapshotId);
      setInlineArchiveBrowser(nextBrowser);
      setSelectedInlineImageId(null);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke hente bildearkivet");
    } finally {
      setInlineArchiveLoading(false);
    }
  }

  async function moveInlineImage(delta: number) {
    if (activeArchiveSnapshot) {
      const nextSnapshotId = delta < 0 ? inlineArchiveBrowser?.previousSnapshotId : inlineArchiveBrowser?.nextSnapshotId;
      if (nextSnapshotId) await showInlineArchiveSnapshot(nextSnapshotId);
      return;
    }
    if (!inlineImages.length) return;
    const nextIndex = activeInlineIndex + delta;
    if (nextIndex < 0 || nextIndex >= inlineImages.length) {
      await moveFromSavedImageToArchive(activeInlineImage?.snapshotId || "", delta);
      return;
    }
    setInlineArchiveBrowser(null);
    setSelectedInlineImageId(inlineImages[nextIndex].id);
  }

  const modalFooter = [
    <Button key="older" className="sun-image-browser-nav-button" disabled={browserLoading || !browser?.canPrevious} onClick={() => openBrowser(browser?.previousSnapshotId)}>
      Arkiv eldre
    </Button>,
    <Button key="newer" className="sun-image-browser-nav-button" disabled={browserLoading || !browser?.canNext} onClick={() => openBrowser(browser?.nextSnapshotId)}>
      Arkiv nyere
    </Button>,
    <Button
      key="ok"
      type="primary"
      className="sun-image-browser-save-button"
      loading={savingImage}
      disabled={browserLoading || !browser?.current}
      onClick={useCurrentImage}
    >
      Lagre 5 bilder
    </Button>,
  ];

  return (
    <div className="sun-session-detail">
      <div className="sun-session-fields">
        {fields.map(([label, value]) => (
          <div className="sun-session-field" key={label}>
            <span>{label}</span>
            <strong>{displayValue(value)}</strong>
          </div>
        ))}
      </div>
      <div className="sun-session-image-panel">
        {activeImageUrl ? (
          <div className="sun-session-inline-browser">
            <img
              src={activeImageUrl}
              alt={`Axis-bilde ${activeImageLabel}`}
              loading="lazy"
            />
            {inlineArchiveLoading ? (
              <div className="sun-session-inline-busy">
                <Spin size="small" />
                <span>Laster bilde</span>
              </div>
            ) : null}
            <div className="sun-session-inline-meta">
              <strong>{activeImagePrefix}</strong>
              <span>{activeImageOffset} - {activeImageLabel}</span>
              {activeImageIsPrimary ? <Tag color="gold">Hovedbilde</Tag> : activeArchiveSnapshot ? <Tag>Arkiv</Tag> : null}
            </div>
            <div className="sun-session-inline-controls">
              <Button
                size="small"
                className="sun-session-inline-nav-button"
                disabled={!canMoveInlinePrevious || inlineArchiveLoading || Boolean(settingPrimarySnapshotId)}
                onClick={() => moveInlineImage(-1)}
              >
                Forrige
              </Button>
              <Button
                size="small"
                className="sun-session-inline-nav-button"
                disabled={!canMoveInlineNext || inlineArchiveLoading || Boolean(settingPrimarySnapshotId)}
                onClick={() => moveInlineImage(1)}
              >
                Neste
              </Button>
              <Button
                size="small"
                type={activeImageIsPrimary ? "default" : "primary"}
                className="sun-session-inline-primary-button"
                loading={settingPrimarySnapshotId === activeSnapshotId}
                disabled={!activeSnapshotId || activeImageIsPrimary || inlineArchiveLoading || Boolean(settingPrimarySnapshotId)}
                onClick={() => saveInlineSnapshotAsPrimary(activeSnapshotId)}
              >
                {activeImageIsPrimary ? "Hovedbilde" : "Sett som hovedbilde"}
              </Button>
              <Button
                size="small"
                className="sun-session-inline-archive-button"
                onClick={() => openBrowser(activeSnapshotId || null)}
                disabled={!canBrowseImages || inlineArchiveLoading}
              >
                Bildearkiv
              </Button>
            </div>
          </div>
        ) : hasImage ? (
          <div className="sun-session-inline-browser">
            <img src={imageUrl} alt={`Axis-bilde for soltime ${displayValue(row.started_at)}`} loading="lazy" />
            <div className="sun-session-inline-controls">
              <Button size="small" onClick={() => openBrowser()} disabled={!canBrowseImages}>
                Bildearkiv
              </Button>
            </div>
          </div>
        ) : (
          <div className="sun-session-empty-image">
            <Typography.Text type="secondary">Ingen koblet bilde for denne soltimen.</Typography.Text>
            <Button size="small" onClick={() => openBrowser()} disabled={!canBrowseImages}>
              Bildearkiv
            </Button>
          </div>
        )}
      </div>
      <Modal
        title="Bildearkiv for soltime"
        open={browserOpen}
        width={980}
        className="sun-image-browser-modal"
        onCancel={() => setBrowserOpen(false)}
        footer={modalFooter}
      >
        <div className="sun-image-browser">
          {browserLoading && !browser?.current ? (
            <div className="sun-image-browser-loading">
              <Spin />
            </div>
          ) : browser?.current ? (
            <div className="sun-image-browser-current">
              {browserLoading ? (
                <div className="sun-image-browser-busy">
                  <Spin size="small" />
                  <span>Laster bilde</span>
                </div>
              ) : null}
              <div className="sun-image-browser-meta">
                <div>
                  <span>Arkivbilde</span>
                  <strong>{browser.current.label}</strong>
                </div>
                <div>
                  <span>Beregnet bildetid</span>
                  <strong>{browser.targetLabel || "-"}</strong>
                </div>
                <div>
                  <span>Avvik</span>
                  <strong>{browser.current.deltaSeconds !== null && browser.current.deltaSeconds !== undefined ? `${displayValue(browser.current.deltaSeconds)} sek` : "-"}</strong>
                </div>
                <div>
                  <span>Status</span>
                  <strong>{browser.current.isLinked ? "Lagret på posten" : "Kan velges"}</strong>
                </div>
              </div>
              <img
                className="sun-image-browser-image"
                src={`${browser.current.imageUrl}?v=${encodeURIComponent(browser.current.id)}`}
                alt={`Axis-bilde ${browser.current.label}`}
              />
            </div>
          ) : (
            <div className="sun-image-browser-empty">
              <Typography.Text type="secondary">Ingen Axis-bilder finnes i arkivet.</Typography.Text>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}

function SunSessionItem({
  row,
  rowKey,
  onImageChanged,
}: {
  row: ModuleRow;
  rowKey: string;
  onImageChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const hasImage = row.has_image === true;
  const imageCount = Number(row.image_count || 0);
  return (
    <details className="sun-session-item" key={rowKey} onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="sun-session-summary">
        <div className="sun-session-main">
          <Typography.Text strong>{displayValue(row.started_at)}</Typography.Text>
          <span>{displayValue(row.room_label || row.room || row.room_id)}</span>
          <span>{displayValue(row.user_name || row.sun2_user_id)}</span>
        </div>
        <div className="sun-session-tags">
          <Tag>{row.duration_minutes ? `${displayValue(row.duration_minutes)} min` : "Tid -"}</Tag>
          <Tag>{row.paid_amount_kr ? `${displayValue(row.paid_amount_kr)} kr` : "Kr -"}</Tag>
          <Tag color={hasImage ? "green" : "default"}>{hasImage ? `${imageCount || 1} bilder` : "Ingen bilde"}</Tag>
        </div>
      </summary>
      {open ? <SunSessionDetails row={row} onImageChanged={onImageChanged} /> : null}
    </details>
  );
}

function SunSessionsPanel({
  table,
  query,
  draftQuery,
  onSearch,
  onClear,
  onDraftChange,
  onImageChanged,
}: {
  table?: ModuleTable;
  query: string;
  draftQuery: string;
  onSearch: (value?: string) => void;
  onClear: () => void;
  onDraftChange: (value: string) => void;
  onImageChanged: () => void;
}) {
  const rows = table ? filterRows(table.rows, table.columns, query) : [];
  return (
    <Card className="table-card sun-sessions-card">
      <TableSearch
        placeholder="Søk i viste soltimer"
        value={draftQuery}
        onValueChange={onDraftChange}
        onClear={onClear}
        onSearch={onSearch}
      />
      <div className="sun-session-list-head">
        <Typography.Text type="secondary">{countText(rows.length, table?.rows.length ?? 0, query)}</Typography.Text>
      </div>
      <div className="sun-session-list">
        {rows.length ? (
          rows.map((row, index) => {
            const key = tableRowKey(row, table?.title ?? "Enkeltimer", index);
            return <SunSessionItem key={key} rowKey={key} row={row} onImageChanged={onImageChanged} />;
          })
        ) : (
          <div className="sun-session-empty">
            <Typography.Text type="secondary">{query.trim() ? "Ingen treff for søket" : "Ingen soltimer å vise"}</Typography.Text>
          </div>
        )}
      </div>
    </Card>
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
