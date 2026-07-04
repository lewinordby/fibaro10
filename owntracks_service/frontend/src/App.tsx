import {
  AimOutlined,
  BuildOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  CompassOutlined,
  DashboardOutlined,
  EditOutlined,
  EnvironmentOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  NodeIndexOutlined,
  PlusOutlined,
  PoweroffOutlined,
  PushpinOutlined,
  ReloadOutlined,
  ToolOutlined,
  UnorderedListOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  Layout,
  Modal,
  Popconfirm,
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
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const { Header, Sider, Content } = Layout;
const MENU_HIDDEN_STORAGE_KEY = "owntracks:mainMenuHidden";
const MAP_LAYER_IDS = ["owntracks-waypoints-fill", "owntracks-waypoints-line", "owntracks-track-line"];
const MAP_SOURCE_IDS = ["owntracks-waypoints", "owntracks-track"];

type ViewKey = "dashboard" | "map" | "visits" | "waypoints" | "suggestions" | "diagnostics" | "messages" | "events" | "build";

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
  origin?: "phone" | "server";
  isSynthetic?: boolean;
  lat?: number;
  lon?: number;
  accuracyM?: number;
  batteryPercent?: number;
  staleMinutes?: number;
  gapMinutes?: number;
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
  source?: string;
  address?: string;
  notes?: string;
  isActive?: boolean;
  lat?: number;
  lon?: number;
  radiusM?: number;
  isInside?: boolean;
  lastState?: string;
  lastEvent?: string;
  lastSeenAt?: string;
};

type WaypointSuggestionRow = {
  id: string;
  topic: string;
  username?: string;
  device?: string;
  suggestedName: string;
  address?: string;
  lat: number;
  lon: number;
  radiusM: number;
  sampleCount: number;
  visits: number;
  totalDuration: string;
  totalDurationSeconds: number;
  firstSeenAt?: string;
  lastSeenAt?: string;
  maxAccuracyM?: number;
  confidence?: number;
};

type WaypointSuggestionsPayload = {
  parameters: Record<string, string | number | boolean>;
  suggestions: WaypointSuggestionRow[];
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

type ZoneSummaryRow = {
  id: string;
  topic: string;
  username?: string;
  device?: string;
  waypointName: string;
  visits: number;
  openVisits: number;
  totalDuration: string;
  totalDurationSeconds: number;
  avgDuration: string;
  avgDurationSeconds: number;
  firstSeenAt?: string;
  lastSeenAt?: string;
  lastStartedAt?: string;
  lastEndedAt?: string;
  lastDuration?: string;
  lastStatus?: string;
  lastConfidence?: number;
  enterSources?: string[];
};

type ZoneSummaryPayload = {
  hours: number;
  generatedAt?: string;
  totals: {
    zones: number;
    visits: number;
    openVisits: number;
    totalDurationSeconds: number;
    totalDuration: string;
  };
  summary: ZoneSummaryRow[];
  activeVisits: VisitRow[];
  recentVisits: VisitRow[];
};

type EventRow = {
  id: number;
  topic: string;
  waypointName: string;
  eventType?: string;
  sourceMessageType?: string;
  origin?: "phone" | "server";
  isSynthetic?: boolean;
  timestamp?: string;
  receivedAt?: string;
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

type DiagnosticRecommendation = {
  severity: "ok" | "info" | "warning" | "bad";
  title: string;
  text: string;
};

type DiagnosticWaypoint = {
  id: number;
  waypointName: string;
  source?: string;
  radiusM?: number;
  insideLocationCount: number;
  nearLocationCount: number;
  minDistanceM?: number;
  lastSeenAt?: string;
  lastPositionAt?: string;
  isInside?: boolean;
};

type DiagnosticGapRow = {
  from: LocationRow;
  to: LocationRow;
  gapMinutes: number;
};

type DiagnosticsPayload = {
  hours: number;
  generatedAt?: string;
  parameters: {
    staleMinutes: number;
    gapMinutes: number;
    maxAccuracyM: number;
    minWaypointRadiusM?: number;
  };
  counts: {
    messages: number;
    locations: number;
    transitions: number;
    statusMessages: number;
    staleLocations: number;
    duplicateLocations: number;
    poorAccuracyLocations: number;
    largeGaps: number;
  };
  accuracy: {
    avgM?: number;
    p50M?: number;
    p90M?: number;
    maxM?: number;
  };
  gaps: {
    avgMinutes?: number;
    p90Minutes?: number;
    maxMinutes?: number;
    rows: DiagnosticGapRow[];
  };
  latest?: LocationRow;
  staleSamples: LocationRow[];
  waypoints: DiagnosticWaypoint[];
  recommendations: DiagnosticRecommendation[];
};

const NAV_ITEMS: Array<{ key: ViewKey; label: string; icon: React.ReactNode; color: string }> = [
  { key: "dashboard", label: "Dashboard", icon: <DashboardOutlined />, color: "#2563eb" },
  { key: "map", label: "Kart", icon: <EnvironmentOutlined />, color: "#0891b2" },
  { key: "visits", label: "Sonebesok", icon: <NodeIndexOutlined />, color: "#15803d" },
  { key: "waypoints", label: "Waypoints", icon: <PushpinOutlined />, color: "#f59e0b" },
  { key: "suggestions", label: "Forslag", icon: <BulbOutlined />, color: "#d97706" },
  { key: "diagnostics", label: "Diagnose", icon: <WarningOutlined />, color: "#dc2626" },
  { key: "messages", label: "Meldinger", icon: <UnorderedListOutlined />, color: "#7c3aed" },
  { key: "events", label: "Hendelser", icon: <ClockCircleOutlined />, color: "#db2777" },
  { key: "build", label: "Build", icon: <BuildOutlined />, color: "#475569" },
];

function viewFromHash(): ViewKey {
  const hash = window.location.hash.replace("#", "");
  return NAV_ITEMS.some((item) => item.key === hash) ? (hash as ViewKey) : "dashboard";
}

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

function escapeHtml(value?: string | number | null) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const replacements: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return replacements[char] || char;
  });
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

function circlePolygon(lon: number, lat: number, radiusM: number, steps = 64) {
  const earthRadiusM = 6_371_008.8;
  const latRad = (lat * Math.PI) / 180;
  const coordinates: number[][] = [];
  for (let index = 0; index <= steps; index += 1) {
    const angle = (index / steps) * Math.PI * 2;
    const dy = Math.sin(angle) * radiusM;
    const dx = Math.cos(angle) * radiusM;
    const pointLat = lat + (dy / earthRadiusM) * (180 / Math.PI);
    const pointLon = lon + (dx / (earthRadiusM * Math.cos(latRad))) * (180 / Math.PI);
    coordinates.push([pointLon, pointLat]);
  }
  return coordinates;
}

function createMapMarker(className: string, label?: string) {
  const element = document.createElement("div");
  element.className = `map-marker ${className}`;
  if (label) element.textContent = label;
  return element;
}

function clearMapOverlays(map: maplibregl.Map, markers: maplibregl.Marker[]) {
  markers.forEach((marker) => marker.remove());
  MAP_LAYER_IDS.forEach((id) => {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  MAP_SOURCE_IDS.forEach((id) => {
    if (map.getSource(id)) map.removeSource(id);
  });
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

function originTag(row: { origin?: "phone" | "server"; isSynthetic?: boolean }) {
  if (row.isSynthetic || row.origin === "server") return <Tag color="purple">Server</Tag>;
  return <Tag color="blue">Telefon</Tag>;
}

function recommendationTag(value?: DiagnosticRecommendation["severity"]) {
  if (value === "bad") return <Tag color="red">Kritisk</Tag>;
  if (value === "warning") return <Tag color="gold">Sjekk</Tag>;
  if (value === "ok") return <Tag color="green">OK</Tag>;
  return <Tag color="blue">Info</Tag>;
}

function staleTag(value?: number) {
  if (value == null) return <Tag>Ukjent</Tag>;
  if (value > 10) return <Tag color="red">{formatNumber(value, 1)} min</Tag>;
  if (value > 2) return <Tag color="gold">{formatNumber(value, 1)} min</Tag>;
  return <Tag color="green">{formatNumber(value, 1)} min</Tag>;
}

function waypointSourceTag(value?: string) {
  if (value === "server-manual") return <Tag color="blue">Lokal</Tag>;
  if (value === "server-suggestion") return <Tag color="gold">Forslag</Tag>;
  return <Tag>Telefon</Tag>;
}

function activeTag(value?: boolean) {
  if (value === false) return <Tag color="red">Av</Tag>;
  return <Tag color="green">Aktiv</Tag>;
}

function waypointSourceLabel(value?: string) {
  if (value === "server-manual") return "Lokal";
  if (value === "server-suggestion") return "Forslag";
  return "Telefon";
}

function durationOrDash(value?: string | null) {
  return value && value !== "-" ? value : "-";
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
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker[]>([]);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (!mapElementRef.current || mapRef.current) return undefined;
    const map = new maplibregl.Map({
      container: mapElementRef.current,
      center: [10.466, 61.115],
      zoom: 13,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          "osm-raster": {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "osm-raster",
            type: "raster",
            source: "osm-raster",
          },
        ],
      },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.on("load", () => setMapReady(true));
    mapRef.current = map;
    window.setTimeout(() => map.resize(), 0);
    return () => {
      markerRef.current.forEach((marker) => marker.remove());
      markerRef.current = [];
      map.remove();
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    window.setTimeout(() => map.resize(), 0);
    clearMapOverlays(map, markerRef.current);
    markerRef.current = [];

    const bounds = new maplibregl.LngLatBounds();
    let hasBounds = false;
    let boundsPointCount = 0;
    let lastBoundPoint: [number, number] | null = null;
    const extendBounds = (lon: number, lat: number) => {
      bounds.extend([lon, lat]);
      hasBounds = true;
      boundsPointCount += 1;
      lastBoundPoint = [lon, lat];
    };
    const points = (data?.locations || []).filter((row) => Number.isFinite(Number(row.lat)) && Number.isFinite(Number(row.lon)));
    if (points.length > 1) {
      map.addSource("owntracks-track", {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: points.map((row) => [Number(row.lon), Number(row.lat)]),
          },
        },
      });
      map.addLayer({
        id: "owntracks-track-line",
        type: "line",
        source: "owntracks-track",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#2563eb", "line-opacity": 0.7, "line-width": 3 },
      });
    }
    points.forEach((row, index) => {
      if (row.lat === undefined || row.lon === undefined) return;
      extendBounds(Number(row.lon), Number(row.lat));
      if (index === points.length - 1) {
        const marker = new maplibregl.Marker({ element: createMapMarker("location-marker"), anchor: "center" })
          .setLngLat([Number(row.lon), Number(row.lat)])
          .setPopup(
            new maplibregl.Popup({ offset: 18 }).setHTML(
              `<b>${escapeHtml(row.topic)}</b><br>${escapeHtml(formatDateTime(row.timestamp || row.receivedAt))}<br>${escapeHtml(formatNumber(row.accuracyM))} m`,
            ),
          )
          .addTo(map);
        markerRef.current.push(marker);
      }
    });
    (data?.devices || []).forEach((row) => {
      if (!Number.isFinite(Number(row.lastLat)) || !Number.isFinite(Number(row.lastLon))) return;
      extendBounds(Number(row.lastLon), Number(row.lastLat));
      const marker = new maplibregl.Marker({ element: createMapMarker("device-marker", "D"), anchor: "center" })
        .setLngLat([Number(row.lastLon), Number(row.lastLat)])
        .setPopup(
          new maplibregl.Popup({ offset: 18 }).setHTML(
            `<b>${escapeHtml(row.topic)}</b><br>Sist sett: ${escapeHtml(formatDateTime(row.lastSeenAt))}<br>${escapeHtml(formatNumber(row.lastAccuracyM))} m`,
          ),
        )
        .addTo(map);
      markerRef.current.push(marker);
    });
    const waypointFeatures = (data?.waypoints || [])
      .filter((row) => Number.isFinite(Number(row.lat)) && Number.isFinite(Number(row.lon)))
      .map((row) => {
        const lat = Number(row.lat);
        const lon = Number(row.lon);
        const radiusM = Number(row.radiusM || 50);
        extendBounds(lon, lat);
        const markerClass = row.source === "server-manual" ? "waypoint-marker local" : row.isInside ? "waypoint-marker inside" : "waypoint-marker";
        const marker = new maplibregl.Marker({ element: createMapMarker(markerClass), anchor: "center" })
          .setLngLat([lon, lat])
          .setPopup(
            new maplibregl.Popup({ offset: 18 }).setHTML(
              `<b>${escapeHtml(row.waypointName)}</b><br>${escapeHtml(row.source === "server-manual" ? "Lokal sone" : "Telefon-sone")}<br>${row.address ? `${escapeHtml(row.address)}<br>` : ""}Radius ${escapeHtml(formatNumber(row.radiusM))} m`,
            ),
          )
          .addTo(map);
        markerRef.current.push(marker);
        return {
          type: "Feature" as const,
          properties: {
            strokeColor: row.source === "server-manual" ? "#2563eb" : row.isInside ? "#15803d" : "#f59e0b",
            fillColor: row.source === "server-manual" ? "#bfdbfe" : row.isInside ? "#86efac" : "#fde68a",
          },
          geometry: {
            type: "Polygon" as const,
            coordinates: [circlePolygon(lon, lat, radiusM)],
          },
        };
      });
    if (waypointFeatures.length) {
      map.addSource("owntracks-waypoints", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: waypointFeatures,
        },
      });
      map.addLayer({
        id: "owntracks-waypoints-fill",
        type: "fill",
        source: "owntracks-waypoints",
        paint: {
          "fill-color": ["get", "fillColor"],
          "fill-opacity": 0.24,
        },
      });
      map.addLayer({
        id: "owntracks-waypoints-line",
        type: "line",
        source: "owntracks-waypoints",
        paint: {
          "line-color": ["get", "strokeColor"],
          "line-opacity": 0.85,
          "line-width": 2,
        },
      });
    }
    if (hasBounds && boundsPointCount === 1 && lastBoundPoint) {
      map.easeTo({ center: lastBoundPoint, zoom: 18, duration: 300 });
    } else if (hasBounds) {
      map.fitBounds(bounds, { padding: 18, maxZoom: 18, duration: 300 });
    }
  }, [data, mapReady]);

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
  const [view, setView] = useState<ViewKey>(() => viewFromHash());
  const [hours, setHours] = useState("24");
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [moduleData, setModuleData] = useState<ModulePayload | null>(null);
  const [mapData, setMapData] = useState<MapPayload | null>(null);
  const [zoneSummary, setZoneSummary] = useState<ZoneSummaryPayload | null>(null);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsPayload | null>(null);
  const [suggestions, setSuggestions] = useState<WaypointSuggestionRow[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionHours, setSuggestionHours] = useState("720");
  const [suggestionMinMinutes, setSuggestionMinMinutes] = useState(10);
  const [suggestionRadiusM, setSuggestionRadiusM] = useState(80);
  const [waypointModalOpen, setWaypointModalOpen] = useState(false);
  const [editingWaypoint, setEditingWaypoint] = useState<WaypointRow | null>(null);
  const [waypointSaving, setWaypointSaving] = useState(false);
  const [waypointMutatingId, setWaypointMutatingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const [waypointForm] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextHealth, nextModule, nextMap, nextZoneSummary, nextDiagnostics] = await Promise.all([
        fetchJson<HealthPayload>("/owntracks/health"),
        fetchJson<ModulePayload>("/owntracks/api/module"),
        fetchJson<MapPayload>("/owntracks/api/map", { hours, limit: 5000 }),
        fetchJson<ZoneSummaryPayload>("/owntracks/api/zone-summary", { hours, limit: 100 }),
        fetchJson<DiagnosticsPayload>("/owntracks/api/diagnostics", { hours }),
      ]);
      setHealth(nextHealth);
      setModuleData(nextModule);
      setMapData(nextMap);
      setZoneSummary(nextZoneSummary);
      setDiagnostics(nextDiagnostics);
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

  useEffect(() => {
    const onHashChange = () => setView(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const topicOptions = useMemo(() => {
    const topics = new Set<string>();
    (mapData?.devices || []).forEach((row) => row.topic && topics.add(row.topic));
    (mapData?.waypoints || []).forEach((row) => row.topic && topics.add(row.topic));
    (mapData?.locations || []).forEach((row) => row.topic && topics.add(row.topic));
    return Array.from(topics).map((topic) => ({ value: topic, label: topic }));
  }, [mapData]);

  const loadSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    try {
      const payload = await fetchJson<WaypointSuggestionsPayload>("/owntracks/api/waypoint-suggestions", {
        hours: suggestionHours,
        min_minutes: suggestionMinMinutes,
        radius_m: suggestionRadiusM,
        limit: 30,
        include_address: 1,
      });
      setSuggestions(payload.suggestions || []);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke hente forslag");
    } finally {
      setSuggestionsLoading(false);
    }
  }, [suggestionHours, suggestionMinMinutes, suggestionRadiusM]);

  useEffect(() => {
    if (view === "suggestions") void loadSuggestions();
  }, [loadSuggestions, view]);

  function openWaypointModal(suggestion?: WaypointSuggestionRow, waypoint?: WaypointRow) {
    setEditingWaypoint(waypoint || null);
    waypointForm.setFieldsValue({
      topic: waypoint?.topic || suggestion?.topic || topicOptions[0]?.value,
      name: waypoint?.waypointName || suggestion?.suggestedName || "",
      lat: waypoint?.lat ?? suggestion?.lat,
      lon: waypoint?.lon ?? suggestion?.lon,
      radiusM: waypoint?.radiusM || suggestion?.radiusM || 100,
      address: waypoint?.address || suggestion?.address || "",
      notes: waypoint?.notes || "",
    });
    setWaypointModalOpen(true);
  }

  function closeWaypointModal() {
    setWaypointModalOpen(false);
    setEditingWaypoint(null);
  }

  async function saveWaypoint() {
    const values = await waypointForm.validateFields();
    setWaypointSaving(true);
    try {
      const result = await fetchJson<{ locationsProcessed: number }>(
        editingWaypoint ? `/owntracks/api/waypoints/${editingWaypoint.id}` : "/owntracks/api/waypoints",
        {},
        {
          method: editingWaypoint ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...values, rebuildHistory: true }),
        },
      );
      message.success(`Waypoint ${editingWaypoint ? "oppdatert" : "opprettet"}. ${result.locationsProcessed || 0} posisjoner ble beregnet paa nytt.`);
      closeWaypointModal();
      await load();
      if (view === "suggestions") await loadSuggestions();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke lagre waypoint");
    } finally {
      setWaypointSaving(false);
    }
  }

  async function disableWaypoint(row: WaypointRow) {
    setWaypointMutatingId(row.id);
    try {
      const result = await fetchJson<{ locationsProcessed: number }>(`/owntracks/api/waypoints/${row.id}`, {}, { method: "DELETE" });
      message.success(`Waypoint deaktivert. ${result.locationsProcessed || 0} posisjoner ble beregnet paa nytt.`);
      await load();
      if (view === "suggestions") await loadSuggestions();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke deaktivere waypoint");
    } finally {
      setWaypointMutatingId(null);
    }
  }

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
  const zoneRows = zoneSummary?.summary || [];
  const activeZoneNames = (zoneSummary?.activeVisits || []).map((row) => row.waypointName).join(", ") || "Ingen aktive";
  const topZone = zoneRows[0];
  const latestLocation = locations[locations.length - 1];

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

  const zoneSummaryColumns: ColumnsType<ZoneSummaryRow> = [
    { title: "Sone", dataIndex: "waypointName", fixed: "left" },
    { title: "Besok", dataIndex: "visits", width: 90 },
    { title: "Apen", dataIndex: "openVisits", width: 90 },
    { title: "Total tid", dataIndex: "totalDuration", width: 120, render: durationOrDash },
    { title: "Snitt", dataIndex: "avgDuration", width: 120, render: durationOrDash },
    { title: "Sist", dataIndex: "lastSeenAt", width: 160, render: formatDateTime },
    { title: "Status", dataIndex: "lastStatus", width: 110, render: statusTag },
    { title: "Kilder", dataIndex: "enterSources", render: (values?: string[]) => (values || []).join(", ") || "-" },
  ];

  const waypointColumns: ColumnsType<WaypointRow> = [
    { title: "Navn", dataIndex: "waypointName", fixed: "left" },
    { title: "Kilde", dataIndex: "source", render: waypointSourceTag },
    { title: "Aktiv", dataIndex: "isActive", render: activeTag },
    { title: "Status", dataIndex: "isInside", render: insideTag },
    { title: "Sist sett", dataIndex: "lastSeenAt", render: formatDateTime },
    { title: "Siste hendelse", dataIndex: "lastEvent", render: eventTag },
    { title: "Radius", dataIndex: "radiusM", render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Adresse", dataIndex: "address", ellipsis: true },
    { title: "Senter", render: (_, row) => mapLink(row.lat, row.lon) },
    {
      title: "",
      width: 170,
      fixed: "right",
      render: (_, row) =>
        row.source === "server-manual" ? (
          <Space size={6}>
            <Button size="small" icon={<EditOutlined />} onClick={() => openWaypointModal(undefined, row)}>
              Rediger
            </Button>
            <Popconfirm title="Deaktiver lokal sone?" okText="Deaktiver" cancelText="Avbryt" onConfirm={() => void disableWaypoint(row)}>
              <Button size="small" danger icon={<PoweroffOutlined />} loading={waypointMutatingId === row.id}>
                Av
              </Button>
            </Popconfirm>
          </Space>
        ) : (
          <Typography.Text type="secondary">{waypointSourceLabel(row.source)}</Typography.Text>
        ),
    },
  ];

  const suggestionColumns: ColumnsType<WaypointSuggestionRow> = [
    { title: "Forslag", dataIndex: "suggestedName", fixed: "left", width: 220 },
    { title: "Adresse", dataIndex: "address", ellipsis: true },
    { title: "Besok", dataIndex: "visits", width: 80 },
    { title: "Tid", dataIndex: "totalDuration", width: 110 },
    { title: "Samples", dataIndex: "sampleCount", width: 90 },
    { title: "Treff", dataIndex: "confidence", width: 90, render: (value?: number) => formatNumber(value, 2) },
    { title: "Sist", dataIndex: "lastSeenAt", width: 150, render: formatDateTime },
    { title: "Radius", dataIndex: "radiusM", width: 100, render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Senter", width: 150, render: (_, row) => mapLink(row.lat, row.lon) },
    {
      title: "",
      width: 120,
      render: (_, row) => (
        <Button size="small" type="primary" onClick={() => openWaypointModal(row)}>
          Opprett
        </Button>
      ),
    },
  ];

  const locationColumns: ColumnsType<LocationRow> = [
    { title: "Tid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Enhet", dataIndex: "topic" },
    { title: "Type", dataIndex: "messageType" },
    { title: "Event", dataIndex: "event", render: eventTag },
    { title: "Opprinnelse", width: 120, render: (_, row) => originTag(row) },
    { title: "Posisjon", render: (_, row) => mapLink(row.lat, row.lon) },
    { title: "Noyaktighet", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Batteri", dataIndex: "batteryPercent", render: (value?: number) => (value == null ? "-" : `${formatNumber(value)} %`) },
  ];

  const eventColumns: ColumnsType<EventRow> = [
    { title: "Tid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Sone", dataIndex: "waypointName" },
    { title: "Hendelse", dataIndex: "eventType", render: eventTag },
    { title: "Opprinnelse", width: 120, render: (_, row) => originTag(row) },
    { title: "Kilde", dataIndex: "sourceMessageType" },
    { title: "Posisjon", render: (_, row) => mapLink(row.lat, row.lon) },
    { title: "Noyaktighet", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
  ];

  const recommendationColumns: ColumnsType<DiagnosticRecommendation> = [
    { title: "Status", dataIndex: "severity", width: 100, render: recommendationTag },
    { title: "Vurdering", dataIndex: "title", width: 240 },
    { title: "Tiltak", dataIndex: "text" },
  ];

  const diagnosticWaypointColumns: ColumnsType<DiagnosticWaypoint> = [
    { title: "Sone", dataIndex: "waypointName", fixed: "left", width: 210 },
    { title: "Kilde", dataIndex: "source", width: 100, render: waypointSourceTag },
    { title: "Status", dataIndex: "isInside", width: 100, render: insideTag },
    { title: "Radius", dataIndex: "radiusM", width: 100, render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Inne", dataIndex: "insideLocationCount", width: 90 },
    { title: "Naer", dataIndex: "nearLocationCount", width: 90 },
    { title: "Min avstand", dataIndex: "minDistanceM", width: 120, render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Sist sett", dataIndex: "lastSeenAt", width: 160, render: formatDateTime },
  ];

  const gapColumns: ColumnsType<DiagnosticGapRow> = [
    { title: "Fra", dataIndex: ["from", "receivedAt"], render: formatDateTime },
    { title: "Til", dataIndex: ["to", "receivedAt"], render: formatDateTime },
    { title: "Hull", dataIndex: "gapMinutes", render: (value?: number) => `${formatNumber(value, 1)} min` },
    { title: "Fra posisjon", render: (_, row) => mapLink(row.from?.lat, row.from?.lon) },
    { title: "Til posisjon", render: (_, row) => mapLink(row.to?.lat, row.to?.lon) },
  ];

  const staleColumns: ColumnsType<LocationRow> = [
    { title: "Mottatt", dataIndex: "receivedAt", render: formatDateTime },
    { title: "Posisjonstid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Alder", dataIndex: "staleMinutes", render: staleTag },
    { title: "Type", dataIndex: "messageType" },
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
            <MetricCard title="Aktiv sone" value={zoneSummary?.totals.openVisits ?? 0} subtitle={activeZoneNames} tone="#15803d" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Sonetid" value={zoneSummary?.totals.totalDuration || "-"} subtitle={`${zoneSummary?.totals.visits ?? 0} besok i valgt periode`} tone="#7c3aed" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Mest tid" value={topZone?.waypointName || "-"} subtitle={topZone ? `${topZone.totalDuration} / ${topZone.visits} besok` : "Ingen sonebesok"} tone="#f59e0b" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Siste posisjon" value={formatDateTime(latestLocation?.timestamp || latestLocation?.receivedAt)} subtitle={latestLocation?.topic || "Ingen posisjon"} tone="#0891b2" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Waypoints" value={health?.counts.waypoints ?? 0} subtitle={`Build ${health?.app.build || "-"}`} tone="#475569" />
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
    [activeZoneNames, health, latestLocation, locations.length, mapData, topZone, visitColumns, visits, zoneSummary],
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
        <SectionHeader title="Sonebesok" subtitle="Oppsummering og siste beregnede/eventstyrte besok per waypoint" />
        <Row gutter={[12, 12]} className="metric-row">
          <Col xs={24} md={8}>
            <MetricCard title="Soner i perioden" value={zoneSummary?.totals.zones ?? 0} subtitle={`${zoneSummary?.totals.visits ?? 0} besok`} tone="#15803d" />
          </Col>
          <Col xs={24} md={8}>
            <MetricCard title="Total sonetid" value={zoneSummary?.totals.totalDuration || "-"} subtitle={`Periode: ${hours === "0" ? "alt" : `${hours} timer`}`} tone="#7c3aed" />
          </Col>
          <Col xs={24} md={8}>
            <MetricCard title="Apen naa" value={zoneSummary?.totals.openVisits ?? 0} subtitle={activeZoneNames} tone="#f59e0b" />
          </Col>
        </Row>
        <Card title="Soneoppsummering" extra={<Typography.Text type="secondary">Sortert paa total tid</Typography.Text>}>
          <DataTable<ZoneSummaryRow> columns={zoneSummaryColumns} data={zoneRows} rowKey="id" />
        </Card>
        <Card title="Siste sonebesok">
          <DataTable<VisitRow> columns={visitColumns} data={visits} />
        </Card>
      </>
    );
  } else if (view === "waypoints") {
    content = (
      <>
        <SectionHeader title="Waypoints" subtitle="Telefonsoner og lokale serverdefinerte soner" />
        <Card
          title="Soner"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={() => openWaypointModal()}>
              Ny lokal sone
            </Button>
          }
        >
          <Table<WaypointRow>
            size="small"
            columns={waypointColumns}
            dataSource={waypoints}
            rowKey="id"
            pagination={{ pageSize: 20, showSizeChanger: false }}
            scroll={{ x: true }}
          />
        </Card>
      </>
    );
  } else if (view === "suggestions") {
    content = (
      <>
        <SectionHeader title="Forslag" subtitle="Mulige lokale soner basert paa steder der telefonen har staatt stille" />
        <Card className="suggestion-control-card">
          <Space wrap>
            <Select
              value={suggestionHours}
              onChange={setSuggestionHours}
              options={[
                { value: "168", label: "Siste 7 dager" },
                { value: "720", label: "Siste 30 dager" },
                { value: "2160", label: "Siste 90 dager" },
                { value: "0", label: "Alt" },
              ]}
            />
            <InputNumber addonBefore="Min stopp" addonAfter="min" min={1} max={1440} value={suggestionMinMinutes} onChange={(value) => setSuggestionMinMinutes(Number(value || 10))} />
            <InputNumber addonBefore="Radius" addonAfter="m" min={15} max={500} value={suggestionRadiusM} onChange={(value) => setSuggestionRadiusM(Number(value || 80))} />
            <Button type="primary" icon={<ReloadOutlined />} loading={suggestionsLoading} onClick={() => void loadSuggestions()}>
              Finn forslag
            </Button>
          </Space>
        </Card>
        <Card title="Stopp som kan bli waypoints" extra={<Typography.Text type="secondary">{suggestions.length} forslag</Typography.Text>}>
          <Table<WaypointSuggestionRow>
            size="small"
            columns={suggestionColumns}
            dataSource={suggestions}
            rowKey="id"
            loading={suggestionsLoading}
            pagination={{ pageSize: 20, showSizeChanger: false }}
            scroll={{ x: true }}
          />
        </Card>
      </>
    );
  } else if (view === "diagnostics") {
    const staleRatio = diagnostics?.counts.locations ? Math.round((diagnostics.counts.staleLocations / diagnostics.counts.locations) * 100) : 0;
    content = (
      <>
        <SectionHeader title="Diagnose" subtitle="Datakvalitet, rapporteringshull og grunnlag for sonebesok" />
        <Row gutter={[12, 12]} className="metric-row">
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Meldinger" value={diagnostics?.counts.messages ?? 0} subtitle={`${diagnostics?.counts.locations ?? 0} med posisjon`} tone="#2563eb" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Gamle posisjoner" value={`${diagnostics?.counts.staleLocations ?? 0}`} subtitle={`${staleRatio}% over ${diagnostics?.parameters.staleMinutes ?? 10} min`} tone={staleRatio > 20 ? "#dc2626" : "#f59e0b"} />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Rapporteringshull" value={diagnostics?.counts.largeGaps ?? 0} subtitle={`Maks ${formatNumber(diagnostics?.gaps.maxMinutes, 1)} min`} tone="#d97706" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Noyaktighet p90" value={formatNumber(diagnostics?.accuracy.p90M)} suffix="m" subtitle={`Snitt ${formatNumber(diagnostics?.accuracy.avgM)} m`} tone="#0891b2" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Gjentatte posisjoner" value={diagnostics?.counts.duplicateLocations ?? 0} subtitle="Samme tid og koordinat" tone="#7c3aed" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Transitions" value={diagnostics?.counts.transitions ?? 0} subtitle={`Generert ${formatDateTime(diagnostics?.generatedAt)}`} tone="#15803d" />
          </Col>
        </Row>
        <Card title="Vurdering og tiltak">
          <Table<DiagnosticRecommendation>
            size="small"
            columns={recommendationColumns}
            dataSource={diagnostics?.recommendations || []}
            rowKey="title"
            pagination={false}
          />
        </Card>
        <Row gutter={[12, 12]}>
          <Col xs={24} xl={12}>
            <Card title="Sonedekning i valgt periode" extra={<Typography.Text type="secondary">{diagnostics?.waypoints.length ?? 0} soner</Typography.Text>}>
              <Table<DiagnosticWaypoint>
                size="small"
                columns={diagnosticWaypointColumns}
                dataSource={diagnostics?.waypoints || []}
                rowKey="id"
                pagination={{ pageSize: 10, showSizeChanger: false }}
                scroll={{ x: true }}
              />
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card title="Rapporteringshull" extra={<Typography.Text type="secondary">Over {diagnostics?.parameters.gapMinutes ?? 20} min</Typography.Text>}>
              <Table<DiagnosticGapRow>
                size="small"
                columns={gapColumns}
                dataSource={diagnostics?.gaps.rows || []}
                rowKey={(row) => `${row.from?.id || "x"}-${row.to?.id || "y"}`}
                pagination={{ pageSize: 10, showSizeChanger: false }}
                scroll={{ x: true }}
              />
            </Card>
          </Col>
        </Row>
        <Card title="Gamle eller gjentatte posisjoner" extra={<Typography.Text type="secondary">Nyeste {diagnostics?.staleSamples.length ?? 0}</Typography.Text>}>
          <Table<LocationRow>
            size="small"
            columns={staleColumns}
            dataSource={diagnostics?.staleSamples || []}
            rowKey="id"
            pagination={{ pageSize: 10, showSizeChanger: false }}
            scroll={{ x: true }}
          />
        </Card>
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
      <Modal
        title={editingWaypoint ? "Rediger lokal waypoint" : "Ny lokal waypoint"}
        open={waypointModalOpen}
        onCancel={closeWaypointModal}
        onOk={() => void saveWaypoint()}
        confirmLoading={waypointSaving}
        okText="Lagre"
        cancelText="Avbryt"
        width={760}
      >
        <Form form={waypointForm} layout="vertical" className="waypoint-form">
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item name="name" label="Navn" rules={[{ required: true, message: "Navn mangler" }]}>
                <Input placeholder="Eks. Hjemme, Lilletorget, Oskar Skoglys veg" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="topic" label="Enhet">
                <Select allowClear disabled={Boolean(editingWaypoint)} placeholder="Bruk siste enhet hvis tom" options={topicOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="lat" label="Latitude" rules={[{ required: true, message: "Latitude mangler" }]}>
                <InputNumber precision={7} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="lon" label="Longitude" rules={[{ required: true, message: "Longitude mangler" }]}>
                <InputNumber precision={7} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="radiusM" label="Radius">
                <InputNumber min={10} max={1000} addonAfter="m" className="full-width-control" />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item name="address" label="Adresse">
                <Input placeholder="Valgfri adresse eller beskrivelse" />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item name="notes" label="Notat">
                <Input.TextArea rows={3} placeholder="Valgfritt notat om sonen" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </AppShell>
  );
}
