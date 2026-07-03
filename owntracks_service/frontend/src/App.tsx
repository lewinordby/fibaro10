import {
  AimOutlined,
  BuildOutlined,
  ClockCircleOutlined,
  CompassOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  NodeIndexOutlined,
  PushpinOutlined,
  ReloadOutlined,
  ToolOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Layout,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const { Header, Sider, Content } = Layout;
const MENU_HIDDEN_STORAGE_KEY = "owntracks:mainMenuHidden";

declare global {
  interface Window {
    L?: any;
  }
}

type ViewKey = "dashboard" | "map" | "visits" | "waypoints" | "messages" | "events" | "build";

type HealthPayload = {
  status: string;
  service: string;
  app: { name: string; version: string; build: string; commit: string };
  database: string;
  ingest: { mode: string; path: string; authTokenEnabled: boolean };
  public: { baseUrl: string; publishUrl: string; adminUrl: string };
  state: {
    lastMessageAt: string | null;
    lastStoreError: string | null;
    messagesReceived: number;
    messagesStored: number;
    messagesDuplicate: number;
  };
  counts: {
    devices: number;
    locations: number;
    waypoints: number;
    events: number;
    zoneVisits: number;
  };
  time: string;
};

type ModulePayload = {
  title: string;
  subtitle: string;
  cards: Array<{ title: string; value: string | number; unit?: string; subtitle?: string }>;
  tables: Array<{ title: string; columns: string[]; rows: Array<Record<string, any>> }>;
  metadata: {
    state: HealthPayload["state"];
    build: HealthPayload["app"];
    buildLog: { currentBuild: string; rows: Array<Record<string, any>> };
  };
};

type LocationRow = {
  id: number;
  topic: string;
  username?: string;
  device?: string;
  receivedAt?: string;
  timestamp?: string;
  messageType?: string;
  event?: string;
  lat?: number;
  lon?: number;
  accuracyM?: number;
  batteryPercent?: number;
};

type DeviceRow = {
  id: number;
  topic: string;
  username?: string;
  device?: string;
  lastSeenAt?: string;
  lastLat?: number;
  lastLon?: number;
  lastAccuracyM?: number;
  lastBatteryPercent?: number;
};

type WaypointRow = {
  id: number;
  topic: string;
  waypointName: string;
  lat?: number;
  lon?: number;
  radiusM?: number;
  isInside?: boolean;
  lastState?: string;
  lastEvent?: string;
  lastSeenAt?: string;
};

type VisitRow = {
  id: number;
  topic: string;
  waypointName: string;
  startedAt?: string;
  endedAt?: string;
  duration?: string;
  status?: string;
  enterSource?: string;
  leaveSource?: string;
  confidence?: number;
};

type EventRow = {
  id: number;
  topic: string;
  waypointName: string;
  eventType?: string;
  sourceMessageType?: string;
  timestamp?: string;
  lat?: number;
  lon?: number;
  accuracyM?: number;
};

type MapPayload = {
  hours: number;
  locations: LocationRow[];
  devices: DeviceRow[];
  waypoints: WaypointRow[];
  zoneVisits: VisitRow[];
};

const NAV_ITEMS: Array<{ key: ViewKey; label: string; icon: React.ReactNode; color: string }> = [
  { key: "dashboard", label: "Dashboard", icon: <DashboardOutlined />, color: "#2563eb" },
  { key: "map", label: "Kart", icon: <EnvironmentOutlined />, color: "#0891b2" },
  { key: "visits", label: "Sonebesok", icon: <NodeIndexOutlined />, color: "#15803d" },
  { key: "waypoints", label: "Waypoints", icon: <PushpinOutlined />, color: "#f59e0b" },
  { key: "messages", label: "Meldinger", icon: <UnorderedListOutlined />, color: "#7c3aed" },
  { key: "events", label: "Hendelser", icon: <ClockCircleOutlined />, color: "#db2777" },
  { key: "build", label: "Build", icon: <BuildOutlined />, color: "#475569" },
];

function tokenFromUrl() {
  return new URLSearchParams(window.location.search).get("token") || "";
}

function apiUrl(path: string, extra: Record<string, string | number> = {}) {
  const url = new URL(path, window.location.origin);
  const token = tokenFromUrl();
  if (token) url.searchParams.set("token", token);
  Object.entries(extra).forEach(([key, value]) => url.searchParams.set(key, String(value)));
  return url.toString();
}

async function fetchJson<T>(path: string, extra: Record<string, string | number> = {}, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path, extra), { credentials: "same-origin", ...init });
  if (response.status === 401) throw new Error("Mangler gyldig OwnTracks-token.");
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("no-NO", { dateStyle: "short", timeStyle: "medium" });
}

function formatNumber(value?: number | null, decimals = 0) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("no-NO", { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
}

function mapLink(lat?: number, lon?: number) {
  if (lat === undefined || lon === undefined || lat === null || lon === null) return "-";
  const label = `${formatNumber(lat, 5)}, ${formatNumber(lon, 5)}`;
  return (
    <a href={`https://www.google.com/maps?q=${encodeURIComponent(`${lat},${lon}`)}`} target="_blank" rel="noreferrer">
      {label}
    </a>
  );
}

function statusTag(status?: string) {
  if (status === "open") return <Tag color="green">Apen</Tag>;
  if (status === "closed") return <Tag>Lukket</Tag>;
  return <Tag>{status || "-"}</Tag>;
}

function insideTag(value?: boolean) {
  if (value === true) return <Tag color="green">Inne</Tag>;
  if (value === false) return <Tag>Ute</Tag>;
  return <Tag color="gold">Ukjent</Tag>;
}

function eventTag(value?: string) {
  if (value === "enter") return <Tag color="green">Enter</Tag>;
  if (value === "leave") return <Tag color="red">Leave</Tag>;
  if (value === "defined") return <Tag color="blue">Definert</Tag>;
  return <Tag>{value || "-"}</Tag>;
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="section-header">
      <div>
        <Typography.Title level={2}>{title}</Typography.Title>
        {subtitle ? <Typography.Text type="secondary">{subtitle}</Typography.Text> : null}
      </div>
    </div>
  );
}

function MetricCard({ title, value, suffix, subtitle, tone }: { title: string; value: string | number; suffix?: string; subtitle?: string; tone?: string }) {
  return (
    <Card className="metric-card" style={{ "--metric-tone": tone || "#2563eb" } as React.CSSProperties}>
      <Statistic title={title} value={value} suffix={suffix} />
      {subtitle ? <Typography.Text type="secondary">{subtitle}</Typography.Text> : null}
    </Card>
  );
}

function DataTable<T extends { id?: number | string }>({ columns, data, rowKey, emptyText }: { columns: ColumnsType<T>; data: T[]; rowKey?: string; emptyText?: string }) {
  if (!data.length) {
    return (
      <Card>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText || "Ingen data enda"} />
      </Card>
    );
  }
  return <Table<T> size="small" columns={columns} dataSource={data} rowKey={rowKey || "id"} pagination={{ pageSize: 20, showSizeChanger: false }} scroll={{ x: true }} />;
}

function OwnTracksMap({ data, large = false }: { data?: MapPayload | null; large?: boolean }) {
  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const layerRef = useRef<any[]>([]);

  useEffect(() => {
    if (!mapElementRef.current || !window.L) return;
    if (!mapRef.current) {
      mapRef.current = window.L.map(mapElementRef.current, { scrollWheelZoom: true });
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(mapRef.current);
      mapRef.current.setView([61.115, 10.466], 13);
    }
    const map = mapRef.current;
    setTimeout(() => map.invalidateSize(), 0);
    layerRef.current.forEach((layer) => map.removeLayer(layer));
    layerRef.current = [];

    const addLayer = (layer: any) => {
      layer.addTo(map);
      layerRef.current.push(layer);
    };

    const bounds: Array<[number, number]> = [];
    const points = (data?.locations || []).filter((row) => Number.isFinite(Number(row.lat)) && Number.isFinite(Number(row.lon)));
    if (points.length > 1) {
      addLayer(window.L.polyline(points.map((row) => [row.lat, row.lon]), { color: "#2563eb", weight: 3, opacity: 0.65 }));
    }
    points.forEach((row, index) => {
      if (row.lat === undefined || row.lon === undefined) return;
      bounds.push([row.lat, row.lon]);
      if (index === points.length - 1) {
        addLayer(
          window.L.circleMarker([row.lat, row.lon], { radius: 7, color: "#2563eb", fillColor: "#2563eb", fillOpacity: 0.9 }).bindPopup(
            `<b>${row.topic}</b><br>${formatDateTime(row.timestamp || row.receivedAt)}<br>${formatNumber(row.accuracyM)} m`,
          ),
        );
      }
    });
    (data?.devices || []).forEach((row) => {
      if (!Number.isFinite(Number(row.lastLat)) || !Number.isFinite(Number(row.lastLon))) return;
      bounds.push([Number(row.lastLat), Number(row.lastLon)]);
      addLayer(
        window.L.marker([row.lastLat, row.lastLon]).bindPopup(
          `<b>${row.topic}</b><br>Sist sett: ${formatDateTime(row.lastSeenAt)}<br>${formatNumber(row.lastAccuracyM)} m`,
        ),
      );
    });
    (data?.waypoints || []).forEach((row) => {
      if (!Number.isFinite(Number(row.lat)) || !Number.isFinite(Number(row.lon))) return;
      bounds.push([Number(row.lat), Number(row.lon)]);
      addLayer(
        window.L.circle([row.lat, row.lon], {
          radius: Number(row.radiusM || 50),
          color: row.isInside ? "#15803d" : "#f59e0b",
          fillColor: row.isInside ? "#bbf7d0" : "#fde68a",
          fillOpacity: 0.22,
          weight: 2,
        }).bindPopup(`<b>${row.waypointName}</b><br>${row.isInside ? "Inne" : "Ute"}<br>Radius ${formatNumber(row.radiusM)} m`),
      );
    });
    if (bounds.length) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 16 });
  }, [data]);

  return <div className={large ? "owntracks-map large" : "owntracks-map"} ref={mapElementRef} />;
}

function BuildFooter({ build }: { build?: string }) {
  return (
    <button className="sider-build-link" type="button" onClick={() => window.dispatchEvent(new CustomEvent("owntracks:view", { detail: "build" }))}>
      <span>Build</span>
      <strong>{build || "-"}</strong>
    </button>
  );
}

function SideNavigation({ active, onChange }: { active: ViewKey; onChange: (key: ViewKey) => void }) {
  return (
    <nav className="sider-nav" aria-label="Hovedmeny">
      <section className="sider-nav-group">
        <div className="sider-nav-label">OwnTracks</div>
        <div className="sider-nav-list">
          {NAV_ITEMS.map((item) => (
            <button
              className={`sider-nav-item ${active === item.key ? "active" : ""}`}
              key={item.key}
              style={{ "--menu-item-color": item.color } as React.CSSProperties}
              type="button"
              onClick={() => onChange(item.key)}
            >
              <span className="sider-nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span className="sider-nav-text">{item.label}</span>
            </button>
          ))}
        </div>
      </section>
    </nav>
  );
}

function AppShell({
  active,
  onViewChange,
  children,
  build,
}: {
  active: ViewKey;
  onViewChange: (key: ViewKey) => void;
  children: React.ReactNode;
  build?: string;
}) {
  const [menuHidden, setMenuHidden] = useState(() => window.localStorage.getItem(MENU_HIDDEN_STORAGE_KEY) === "1");

  useEffect(() => {
    window.localStorage.setItem(MENU_HIDDEN_STORAGE_KEY, menuHidden ? "1" : "0");
  }, [menuHidden]);

  useEffect(() => {
    const listener = (event: Event) => {
      const detail = (event as CustomEvent<ViewKey>).detail;
      if (detail) onViewChange(detail);
    };
    window.addEventListener("owntracks:view", listener);
    return () => window.removeEventListener("owntracks:view", listener);
  }, [onViewChange]);

  return (
    <Layout className={`app-shell ${menuHidden ? "main-menu-hidden" : ""}`}>
      <Sider width={218} collapsedWidth={0} collapsed={menuHidden} trigger={null} className="app-sider">
        <div className="sider-brand">
          <div className="brand-mark">
            <CompassOutlined />
          </div>
          <div>
            <strong>OwnTracks</strong>
            <span>Lilletorget</span>
          </div>
        </div>
        <SideNavigation active={active} onChange={onViewChange} />
        <BuildFooter build={build} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="app-header-left">
            <Button
              className="main-menu-toggle"
              type="text"
              icon={menuHidden ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setMenuHidden((value) => !value)}
              aria-label={menuHidden ? "Vis hovedmeny" : "Skjul hovedmeny"}
              title={menuHidden ? "Vis hovedmeny" : "Skjul hovedmeny"}
            />
            <Typography.Text strong>{NAV_ITEMS.find((item) => item.key === active)?.label || "OwnTracks"}</Typography.Text>
          </div>
          <Typography.Text type="secondary">HTTP-mottak for posisjoner, waypoints og sonebesok</Typography.Text>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  const [view, setView] = useState<ViewKey>(() => (window.location.hash.replace("#", "") as ViewKey) || "dashboard");
  const [hours, setHours] = useState("24");
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [moduleData, setModuleData] = useState<ModulePayload | null>(null);
  const [mapData, setMapData] = useState<MapPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rebuilding, setRebuilding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextHealth, nextModule, nextMap] = await Promise.all([
        fetchJson<HealthPayload>("/owntracks/health"),
        fetchJson<ModulePayload>("/owntracks/api/module"),
        fetchJson<MapPayload>("/owntracks/api/map", { hours, limit: 5000 }),
      ]);
      setHealth(nextHealth);
      setModuleData(nextModule);
      setMapData(nextMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ukjent feil ved lasting");
    } finally {
      setLoading(false);
    }
  }, [hours]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    window.location.hash = view;
  }, [view]);

  async function rebuildVisits() {
    setRebuilding(true);
    try {
      const result = await fetchJson<{ locationsProcessed: number }>("/owntracks/api/rebuild", {}, { method: "POST" });
      message.success(`Sonebesok bygget fra ${result.locationsProcessed} posisjoner`);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Rebuild feilet");
    } finally {
      setRebuilding(false);
    }
  }

  const visits = mapData?.zoneVisits || [];
  const waypoints = mapData?.waypoints || [];
  const locations = mapData?.locations || [];
  const events = (moduleData?.tables.find((table) => table.title === "Waypoint-hendelser")?.rows || []) as EventRow[];
  const buildRows = moduleData?.metadata.buildLog.rows || [];

  const visitColumns: ColumnsType<VisitRow> = [
    { title: "Sone", dataIndex: "waypointName", fixed: "left" },
    { title: "Start", dataIndex: "startedAt", render: formatDateTime },
    { title: "Slutt", dataIndex: "endedAt", render: formatDateTime },
    { title: "Varighet", dataIndex: "duration" },
    { title: "Status", dataIndex: "status", render: statusTag },
    { title: "Kilde inn", dataIndex: "enterSource" },
    { title: "Kilde ut", dataIndex: "leaveSource" },
    { title: "Treff", dataIndex: "confidence", render: (value?: number) => formatNumber(value, 3) },
  ];

  const waypointColumns: ColumnsType<WaypointRow> = [
    { title: "Navn", dataIndex: "waypointName", fixed: "left" },
    { title: "Status", dataIndex: "isInside", render: insideTag },
    { title: "Sist sett", dataIndex: "lastSeenAt", render: formatDateTime },
    { title: "Siste hendelse", dataIndex: "lastEvent", render: eventTag },
    { title: "Radius", dataIndex: "radiusM", render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Senter", render: (_, row) => mapLink(row.lat, row.lon) },
  ];

  const locationColumns: ColumnsType<LocationRow> = [
    { title: "Tid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Enhet", dataIndex: "topic" },
    { title: "Type", dataIndex: "messageType" },
    { title: "Event", dataIndex: "event", render: eventTag },
    { title: "Posisjon", render: (_, row) => mapLink(row.lat, row.lon) },
    { title: "Noyaktighet", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Batteri", dataIndex: "batteryPercent", render: (value?: number) => (value == null ? "-" : `${formatNumber(value)} %`) },
  ];

  const eventColumns: ColumnsType<EventRow> = [
    { title: "Tid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Sone", dataIndex: "waypointName" },
    { title: "Hendelse", dataIndex: "eventType", render: eventTag },
    { title: "Kilde", dataIndex: "sourceMessageType" },
    { title: "Posisjon", render: (_, row) => mapLink(row.lat, row.lon) },
    { title: "Noyaktighet", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
  ];

  const buildColumns: ColumnsType<Record<string, any>> = [
    { title: "Build", dataIndex: "build", width: 90 },
    { title: "Dato", dataIndex: "date", width: 130 },
    { title: "Overskrift", dataIndex: "headline", width: 260 },
    { title: "Endringer", dataIndex: "changes", render: (changes?: string[]) => (changes || []).map((change) => <div key={change}>{change}</div>) },
  ];

  const controls = (
    <Space wrap>
      <Select
        value={hours}
        onChange={setHours}
        options={[
          { value: "24", label: "Siste 24 timer" },
          { value: "168", label: "Siste 7 dager" },
          { value: "720", label: "Siste 30 dager" },
          { value: "0", label: "Alt" },
        ]}
      />
      <Button icon={<ToolOutlined />} loading={rebuilding} onClick={rebuildVisits}>
        Bygg sonebesok
      </Button>
      <Button type="primary" icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>
        Oppdater
      </Button>
    </Space>
  );

  const dashboard = useMemo(
    () => (
      <>
        <SectionHeader title="Dashboard" subtitle={health?.public.publishUrl || "OwnTracks HTTP-mottak"} />
        <Row gutter={[12, 12]} className="metric-row">
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Status" value={health?.status || "-"} subtitle={health?.database === "ok" ? "Database OK" : "Database ukjent"} tone="#15803d" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Meldinger" value={health?.counts.locations ?? 0} subtitle={`${health?.state.messagesDuplicate ?? 0} dubletter`} tone="#2563eb" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Enheter" value={health?.counts.devices ?? 0} subtitle="Telefoner/enheter" tone="#0891b2" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Waypoints" value={health?.counts.waypoints ?? 0} subtitle="Definerte soner" tone="#f59e0b" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Sonebesok" value={health?.counts.zoneVisits ?? 0} subtitle="Beregnet og eventstyrt" tone="#15803d" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Build" value={health?.app.build || "-"} subtitle={health?.app.commit || ""} tone="#475569" />
          </Col>
        </Row>
        <Row gutter={[12, 12]}>
          <Col xs={24} xl={15}>
            <Card title="Kart og siste spor" extra={<Typography.Text type="secondary">{locations.length} posisjoner</Typography.Text>}>
              <OwnTracksMap data={mapData} />
            </Card>
          </Col>
          <Col xs={24} xl={9}>
            <Card title="Siste sonebesok">
              <DataTable<VisitRow> columns={visitColumns.slice(0, 5)} data={visits.slice(0, 8)} />
            </Card>
          </Col>
        </Row>
      </>
    ),
    [health, locations.length, mapData, visitColumns, visits],
  );

  let content: React.ReactNode = dashboard;
  if (view === "map") {
    content = (
      <>
        <SectionHeader title="Kart" subtitle={`${locations.length} posisjoner, ${waypoints.length} waypoints`} />
        <Card title="Spor og soner">
          <OwnTracksMap data={mapData} large />
        </Card>
      </>
    );
  } else if (view === "visits") {
    content = (
      <>
        <SectionHeader title="Sonebesok" subtitle="Beregnede og eventstyrte besok per waypoint" />
        <DataTable<VisitRow> columns={visitColumns} data={visits} />
      </>
    );
  } else if (view === "waypoints") {
    content = (
      <>
        <SectionHeader title="Waypoints" subtitle="Soner publisert fra OwnTracks-appen" />
        <DataTable<WaypointRow> columns={waypointColumns} data={waypoints} />
      </>
    );
  } else if (view === "messages") {
    content = (
      <>
        <SectionHeader title="Meldinger" subtitle="Alle posisjonsmeldinger i valgt periode" />
        <DataTable<LocationRow> columns={locationColumns} data={[...locations].reverse()} />
      </>
    );
  } else if (view === "events") {
    content = (
      <>
        <SectionHeader title="Hendelser" subtitle="Waypoint-definisjoner, enter og leave" />
        <DataTable<EventRow> columns={eventColumns} data={events} />
      </>
    );
  } else if (view === "build") {
    content = (
      <>
        <SectionHeader title="Build" subtitle="Egen buildlogg for OwnTracks-tjenesten" />
        <DataTable<Record<string, any>> columns={buildColumns} data={buildRows} rowKey="build" />
      </>
    );
  }

  return (
    <AppShell active={view} onViewChange={setView} build={health?.app.build}>
      <div className="content-toolbar">
        <div className="status-block">
          <Tag color={health?.status === "ok" ? "green" : "red"}>{health?.status || "laster"}</Tag>
          <Typography.Text type="secondary">Siste melding: {formatDateTime(health?.state.lastMessageAt)}</Typography.Text>
          {health?.state.lastStoreError ? <Tag color="red">{health.state.lastStoreError}</Tag> : null}
        </div>
        {controls}
      </div>
      {error ? <Alert className="page-alert" type="error" message={error} showIcon /> : null}
      {content}
    </AppShell>
  );
}
