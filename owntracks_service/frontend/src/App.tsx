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
  Segmented,
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
import type {
  DeviceRow,
  DiagnosticGapRow,
  DiagnosticRecommendation,
  DiagnosticsPayload,
  DiagnosticWaypoint,
  EventRow,
  HealthPayload,
  LocationRow,
  MapPayload,
  MessageGroupRow,
  ModulePayload,
  TimeFilterMode,
  ViewKey,
  VisitDisplayRow,
  VisitRow,
  WaypointRow,
  WaypointSuggestionRow,
  WaypointSuggestionsPayload,
  ZoneSummaryPayload,
  ZoneSummaryRow,
} from "./types";

const { Header, Sider, Content } = Layout;
const MENU_HIDDEN_STORAGE_KEY = "owntracks:mainMenuHidden";
const MAP_LAYER_IDS = ["owntracks-waypoints-fill", "owntracks-waypoints-line", "owntracks-track-line"];
const MAP_SOURCE_IDS = ["owntracks-waypoints", "owntracks-track"];
const CATEGORY_ALL = "__all__";
const CATEGORY_NONE = "__none__";

const NAV_ITEMS: Array<{ key: ViewKey; label: string; icon: React.ReactNode; color: string }> = [
  { key: "dashboard", label: "Dashboard", icon: <DashboardOutlined />, color: "#2563eb" },
  { key: "places", label: "Kjente steder", icon: <AimOutlined />, color: "#15803d" },
  { key: "occupancy", label: "Opphold", icon: <ClockCircleOutlined />, color: "#7c3aed" },
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
  if (hash.startsWith("place:")) return "places";
  return NAV_ITEMS.some((item) => item.key === hash) ? (hash as ViewKey) : "dashboard";
}

function placeKey(topic?: string, waypointName?: string) {
  return JSON.stringify([topic || "", waypointName || ""]);
}

function placeKeyFromHash() {
  const hash = window.location.hash.replace("#", "");
  if (!hash.startsWith("place:")) return null;
  try {
    return decodeURIComponent(hash.slice("place:".length));
  } catch {
    return null;
  }
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

function formatDateTimeLocalInput(date: Date) {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function localInputToIso(value?: string) {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString();
}

function timestampMs(value?: string | null) {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.getTime();
}

function relativePeriodLabel(hours: string) {
  if (hours === "6") return "Siste 6 timer";
  if (hours === "12") return "Siste 12 timer";
  if (hours === "24") return "Siste 24 timer";
  if (hours === "168") return "Siste 7 dager";
  if (hours === "720") return "Siste 30 dager";
  if (hours === "0") return "Alt";
  return `Siste ${hours} timer`;
}

function coordinateKey(value?: number | null) {
  return value === undefined || value === null ? "" : Number(value).toFixed(7);
}

function addSetValue(target: Set<string>, value?: string | null) {
  if (value) target.add(value);
}

type MessageGroupAccumulator = Omit<MessageGroupRow, "messageTypes" | "events"> & {
  messageTypeSet: Set<string>;
  eventSet: Set<string>;
  firstReceivedMs?: number;
  lastReceivedMs?: number;
};

function compactMessageRows(rows: LocationRow[]) {
  const groups = new Map<string, MessageGroupAccumulator>();
  rows.forEach((row) => {
    const key = [row.topic, row.timestamp || "", coordinateKey(row.lat), coordinateKey(row.lon)].join("|");
    const receivedMs = timestampMs(row.receivedAt || row.timestamp);
    let group = groups.get(key);
    if (!group) {
      group = {
        id: key,
        topic: row.topic,
        timestamp: row.timestamp,
        firstReceivedAt: row.receivedAt,
        lastReceivedAt: row.receivedAt,
        count: 0,
        messageTypeSet: new Set<string>(),
        eventSet: new Set<string>(),
        lat: row.lat,
        lon: row.lon,
        distanceFromPreviousM: row.distanceFromPreviousM,
        accuracyM: row.accuracyM,
        usableForCalculation: row.usableForCalculation,
        accuracyLimitM: row.accuracyLimitM,
        batteryPercent: row.batteryPercent,
        firstReceivedMs: receivedMs,
        lastReceivedMs: receivedMs,
      };
      groups.set(key, group);
    }
    group.count += 1;
    addSetValue(group.messageTypeSet, row.messageType);
    addSetValue(group.eventSet, row.event);
    if (group.distanceFromPreviousM == null && row.distanceFromPreviousM != null) group.distanceFromPreviousM = row.distanceFromPreviousM;
    if (receivedMs !== undefined && (group.firstReceivedMs === undefined || receivedMs < group.firstReceivedMs)) {
      group.firstReceivedMs = receivedMs;
      group.firstReceivedAt = row.receivedAt;
    }
    if (receivedMs !== undefined && (group.lastReceivedMs === undefined || receivedMs >= group.lastReceivedMs)) {
      group.lastReceivedMs = receivedMs;
      group.lastReceivedAt = row.receivedAt;
      group.accuracyM = row.accuracyM;
      group.usableForCalculation = row.usableForCalculation;
      group.accuracyLimitM = row.accuracyLimitM;
      group.batteryPercent = row.batteryPercent;
    }
  });
  return Array.from(groups.values())
    .map(({ messageTypeSet, eventSet, firstReceivedMs, lastReceivedMs, ...row }) => ({
      ...row,
      messageTypes: Array.from(messageTypeSet),
      events: Array.from(eventSet),
    }))
    .sort((left, right) => (timestampMs(right.lastReceivedAt || right.timestamp) || 0) - (timestampMs(left.lastReceivedAt || left.timestamp) || 0));
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

function stateUseTag(row: { ignoredForState?: boolean; ignoredReason?: string }) {
  if (row.ignoredForState) {
    return (
      <Tag color="gold" title={row.ignoredReason || "Lagret som raadata, men brukt ikke i inne/ute-status."}>
        Raadata
      </Tag>
    );
  }
  return <Tag color="green">Styrer status</Tag>;
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

function calculationUseTag(row: { usableForCalculation?: boolean; accuracyM?: number; accuracyLimitM?: number }) {
  if (row.usableForCalculation === false) {
    return (
      <Tag color="gold" title={`Ignoreres i beregninger${row.accuracyLimitM ? ` over ${formatNumber(row.accuracyLimitM)} m` : ""}`}>
        Lav presisjon
      </Tag>
    );
  }
  return <Tag color="green">Brukes</Tag>;
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

function categoryTag(value?: string) {
  return value ? <Tag color="blue">{value}</Tag> : <Typography.Text type="secondary">Uten kategori</Typography.Text>;
}

function categoryFilterValue(value?: string | null) {
  return value ? value : CATEGORY_NONE;
}

function categoryMatches(value: string | undefined | null, selected: string) {
  return selected === CATEGORY_ALL || categoryFilterValue(value) === selected;
}

function durationOrDash(value?: string | null) {
  return value && value !== "-" ? value : "-";
}

function durationSecondsLabel(seconds?: number | null) {
  const totalSeconds = Math.max(0, Math.round(Number(seconds || 0)));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (days > 0) return `${days} d ${hours} t`;
  if (hours > 0) return `${hours} t ${minutes} min`;
  return `${minutes} min`;
}

function visitEffectiveSeconds(row: VisitRow) {
  if (typeof row.durationSeconds === "number") return Math.max(0, row.durationSeconds);
  const startMs = timestampMs(row.startedAt);
  if (startMs === undefined) return 0;
  const endMs = timestampMs(row.endedAt) || Date.now();
  return Math.max(0, Math.round((endMs - startMs) / 1000));
}

function visitDuration(row: VisitRow) {
  if (row.status === "open" && row.startedAt) {
    const startMs = timestampMs(row.startedAt);
    if (startMs !== undefined) return durationSecondsLabel((Date.now() - startMs) / 1000);
  }
  return row.duration || durationSecondsLabel(row.durationSeconds);
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
            maxzoom: 19,
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

    const primaryBounds = new maplibregl.LngLatBounds();
    const fallbackBounds = new maplibregl.LngLatBounds();
    let primaryPointCount = 0;
    let fallbackPointCount = 0;
    let lastPrimaryPoint: [number, number] | null = null;
    let lastFallbackPoint: [number, number] | null = null;
    const extendPrimaryBounds = (lon: number, lat: number) => {
      primaryBounds.extend([lon, lat]);
      primaryPointCount += 1;
      lastPrimaryPoint = [lon, lat];
    };
    const extendFallbackBounds = (lon: number, lat: number) => {
      fallbackBounds.extend([lon, lat]);
      fallbackPointCount += 1;
      lastFallbackPoint = [lon, lat];
    };
    const points = (data?.mapLocations || []).filter((row) => Number.isFinite(Number(row.lat)) && Number.isFinite(Number(row.lon)));
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
      extendPrimaryBounds(Number(row.lon), Number(row.lat));
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
      if (row.lastUsableForCalculation === false) return;
      if (!Number.isFinite(Number(row.lastLat)) || !Number.isFinite(Number(row.lastLon))) return;
      extendFallbackBounds(Number(row.lastLon), Number(row.lastLat));
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
        extendFallbackBounds(lon, lat);
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
    const fitPadding = large ? 44 : 30;
    if (primaryPointCount === 1 && lastPrimaryPoint) {
      map.easeTo({ center: lastPrimaryPoint, zoom: 19, duration: 300 });
    } else if (primaryPointCount > 1) {
      map.fitBounds(primaryBounds, { padding: fitPadding, maxZoom: 19, duration: 300 });
    } else if (fallbackPointCount === 1 && lastFallbackPoint) {
      map.easeTo({ center: lastFallbackPoint, zoom: 17, duration: 300 });
    } else if (fallbackPointCount > 1) {
      map.fitBounds(fallbackBounds, { padding: fitPadding, maxZoom: 17, duration: 300 });
    }
  }, [data, large, mapReady]);

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
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(() => placeKeyFromHash());
  const [hours, setHours] = useState("24");
  const [timeFilterMode, setTimeFilterMode] = useState<TimeFilterMode>("relative");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [categoryFilter, setCategoryFilter] = useState(CATEGORY_ALL);
  const [messageView, setMessageView] = useState<"grouped" | "raw">("grouped");
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

  const timeParams = useMemo(() => {
    if (timeFilterMode !== "custom") return { hours };
    const params: Record<string, string | number> = { hours: 0 };
    const startIso = localInputToIso(customStart);
    const endIso = localInputToIso(customEnd);
    if (startIso) params.start = startIso;
    if (endIso) params.end = endIso;
    return params;
  }, [customEnd, customStart, hours, timeFilterMode]);

  const timeFilterLabel = useMemo(() => {
    if (timeFilterMode !== "custom") return relativePeriodLabel(hours);
    const fromLabel = customStart ? formatDateTime(localInputToIso(customStart)) : "start";
    const toLabel = customEnd ? formatDateTime(localInputToIso(customEnd)) : "naa";
    return `${fromLabel} - ${toLabel}`;
  }, [customEnd, customStart, hours, timeFilterMode]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextHealth, nextModule, nextMap, nextZoneSummary, nextDiagnostics] = await Promise.all([
        fetchJson<HealthPayload>("/owntracks/health"),
        fetchJson<ModulePayload>("/owntracks/api/module"),
        fetchJson<MapPayload>("/owntracks/api/map", { ...timeParams, limit: 5000 }),
        fetchJson<ZoneSummaryPayload>("/owntracks/api/zone-summary", { ...timeParams, limit: 100 }),
        fetchJson<DiagnosticsPayload>("/owntracks/api/diagnostics", timeParams),
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
  }, [timeParams]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    window.location.hash = view;
  }, [view]);

  useEffect(() => {
    const onHashChange = () => {
      const nextPlaceId = placeKeyFromHash();
      if (nextPlaceId) {
        setSelectedPlaceId(nextPlaceId);
        setView("places");
        return;
      }
      setSelectedPlaceId(null);
      setView(viewFromHash());
    };
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

  const visits = mapData?.zoneVisits || [];
  const waypoints = mapData?.waypoints || [];
  const locations = mapData?.locations || [];
  const mapLocations = mapData?.mapLocations || locations.filter((row) => row.usableForCalculation !== false);
  const qualityPolicy = mapData?.qualityPolicy || health?.qualityPolicy;
  const maxCalculationAccuracyM = qualityPolicy?.maxCalculationAccuracyM ?? 30;
  const ignoredForAccuracy = mapData?.qualityPolicy?.ignoredForAccuracy ?? locations.filter((row) => row.usableForCalculation === false).length;
  const precisionPolicyText = `Raadata lagres alltid. Kartspor, sonebesok og waypointforslag bruker punkter med presisjon maks ${formatNumber(maxCalculationAccuracyM)} m.`;

  const loadSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    try {
      const payload = await fetchJson<WaypointSuggestionsPayload>("/owntracks/api/waypoint-suggestions", {
        hours: suggestionHours,
        min_minutes: suggestionMinMinutes,
        radius_m: suggestionRadiusM,
        max_accuracy_m: maxCalculationAccuracyM,
        limit: 30,
        include_address: 1,
      });
      setSuggestions(payload.suggestions || []);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kunne ikke hente forslag");
    } finally {
      setSuggestionsLoading(false);
    }
  }, [maxCalculationAccuracyM, suggestionHours, suggestionMinMinutes, suggestionRadiusM]);

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
      category: waypoint?.category ? [waypoint.category] : [],
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
    const payload = {
      ...values,
      category: Array.isArray(values.category) ? values.category[0] || "" : values.category || "",
      rebuildHistory: true,
    };
    setWaypointSaving(true);
    try {
      const result = await fetchJson<{ locationsProcessed: number }>(
        editingWaypoint ? `/owntracks/api/waypoints/${editingWaypoint.id}` : "/owntracks/api/waypoints",
        {},
        {
          method: editingWaypoint ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
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

  const groupedMessages = useMemo(() => compactMessageRows(locations), [locations]);
  const events = (moduleData?.tables.find((table) => table.title === "Waypoint-hendelser")?.rows || []) as EventRow[];
  const filteredEvents = events.filter((row) => {
    const rowMs = timestampMs(row.timestamp || row.receivedAt);
    if (rowMs === undefined) return true;
    if (timeFilterMode === "custom") {
      const startMs = timestampMs(localInputToIso(customStart));
      const endMs = timestampMs(localInputToIso(customEnd));
      return (startMs === undefined || rowMs >= startMs) && (endMs === undefined || rowMs <= endMs);
    }
    if (hours === "0") return true;
    return rowMs >= Date.now() - Number(hours) * 60 * 60 * 1000;
  });
  const buildRows = moduleData?.metadata.buildLog.rows || [];
  const zoneRows = zoneSummary?.summary || [];
  const rawPlaceRows = zoneSummary?.places || zoneRows;
  const waypointByPlace = useMemo(() => {
    const result = new Map<string, WaypointRow>();
    waypoints.forEach((row) => result.set(placeKey(row.topic, row.waypointName), row));
    rawPlaceRows.forEach((row) => row.waypoint && result.set(placeKey(row.topic, row.waypointName), row.waypoint));
    return result;
  }, [rawPlaceRows, waypoints]);
  const categoryOptions = useMemo(() => {
    const categories = new Set<string>();
    waypoints.forEach((row) => row.category && categories.add(row.category));
    rawPlaceRows.forEach((row) => row.waypoint?.category && categories.add(row.waypoint.category));
    return Array.from(categories).sort((left, right) => left.localeCompare(right, "no")).map((value) => ({ value, label: value }));
  }, [rawPlaceRows, waypoints]);
  const categoryFilterOptions = useMemo(
    () => [
      { value: CATEGORY_ALL, label: "Alle kategorier" },
      { value: CATEGORY_NONE, label: "Uten kategori" },
      ...categoryOptions,
    ],
    [categoryOptions],
  );
  const placeRows = useMemo(
    () => rawPlaceRows.filter((row) => categoryMatches(row.waypoint?.category, categoryFilter)),
    [categoryFilter, rawPlaceRows],
  );
  const filteredWaypoints = useMemo(
    () => waypoints.filter((row) => categoryMatches(row.category, categoryFilter)),
    [categoryFilter, waypoints],
  );
  const visitsWithPlace = useMemo<VisitDisplayRow[]>(
    () =>
      visits.map((row) => {
        const waypoint = waypointByPlace.get(placeKey(row.topic, row.waypointName));
        return {
          ...row,
          category: waypoint?.category,
          address: waypoint?.address,
          totalDurationSeconds: row.durationSeconds ?? visitEffectiveSeconds(row),
        };
      }),
    [visits, waypointByPlace],
  );
  const filteredVisits = useMemo(
    () => visitsWithPlace.filter((row) => categoryMatches(row.category, categoryFilter)),
    [categoryFilter, visitsWithPlace],
  );
  const filteredMapData = useMemo<MapPayload | null>(() => {
    if (!mapData || categoryFilter === CATEGORY_ALL) return mapData;
    return {
      ...mapData,
      waypoints: filteredWaypoints,
      zoneVisits: filteredVisits,
    };
  }, [categoryFilter, filteredVisits, filteredWaypoints, mapData]);
  const selectedPlace = selectedPlaceId ? placeRows.find((row) => placeKey(row.topic, row.waypointName) === selectedPlaceId) || null : null;
  const activePlace = selectedPlace || placeRows[0] || null;
  const selectedPlaceVisits = activePlace
    ? filteredVisits
        .filter((row) => row.topic === activePlace.topic && row.waypointName === activePlace.waypointName)
        .sort((left, right) => (timestampMs(right.startedAt) || 0) - (timestampMs(left.startedAt) || 0))
    : [];
  const selectedPlaceMapData = activePlace
    ? ({
        hours: mapData?.hours ?? Number(hours),
        locations: [],
        mapLocations: selectedPlaceVisits.flatMap((visit, index) => {
          const rows: LocationRow[] = [];
          if (visit.startLat !== undefined && visit.startLon !== undefined) {
            rows.push({
              id: -1_000_000 - index * 3,
              topic: visit.topic,
              timestamp: visit.startedAt,
              lat: visit.startLat,
              lon: visit.startLon,
              usableForCalculation: true,
            });
          }
          if (visit.endedAt && visit.endLat !== undefined && visit.endLon !== undefined) {
            rows.push({
              id: -1_000_001 - index * 3,
              topic: visit.topic,
              timestamp: visit.endedAt,
              lat: visit.endLat,
              lon: visit.endLon,
              usableForCalculation: true,
            });
          } else if (visit.lastLat !== undefined && visit.lastLon !== undefined) {
            rows.push({
              id: -1_000_002 - index * 3,
              topic: visit.topic,
              timestamp: visit.startedAt,
              lat: visit.lastLat,
              lon: visit.lastLon,
              usableForCalculation: true,
            });
          }
          return rows;
        }),
        devices: [],
        waypoints: activePlace.waypoint ? [activePlace.waypoint] : filteredWaypoints.filter((row) => row.topic === activePlace.topic && row.waypointName === activePlace.waypointName),
        zoneVisits: selectedPlaceVisits,
      } satisfies MapPayload)
    : null;
  const filteredActiveVisits = useMemo(
    () =>
      (zoneSummary?.activeVisits || []).filter((row) => {
        const waypoint = waypointByPlace.get(placeKey(row.topic, row.waypointName));
        return categoryMatches(waypoint?.category, categoryFilter);
      }),
    [categoryFilter, waypointByPlace, zoneSummary],
  );
  const activeZoneNames = filteredActiveVisits.map((row) => row.waypointName).join(", ") || "Ingen aktive";
  const latestUsableLocation = mapLocations[mapLocations.length - 1];
  const occupancyRows = useMemo(
    () => [...filteredVisits].sort((left, right) => (timestampMs(right.startedAt) || 0) - (timestampMs(left.startedAt) || 0)),
    [filteredVisits],
  );
  const occupancyTotalSeconds = useMemo(
    () => occupancyRows.reduce((sum, row) => sum + visitEffectiveSeconds(row), 0),
    [occupancyRows],
  );
  const occupancyCategoryRows = useMemo(() => {
    const grouped = new Map<string, { id: string; category: string; visits: number; totalDurationSeconds: number; openVisits: number }>();
    occupancyRows.forEach((row) => {
      const id = categoryFilterValue(row.category);
      const current = grouped.get(id) || {
        id,
        category: row.category || "Uten kategori",
        visits: 0,
        totalDurationSeconds: 0,
        openVisits: 0,
      };
      current.visits += 1;
      current.totalDurationSeconds += visitEffectiveSeconds(row);
      if (row.status === "open") current.openVisits += 1;
      grouped.set(id, current);
    });
    return Array.from(grouped.values()).sort((left, right) => right.totalDurationSeconds - left.totalDurationSeconds);
  }, [occupancyRows]);

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

  const placeVisitColumns: ColumnsType<VisitRow> = [
    { title: "Kom", dataIndex: "startedAt", width: 190, render: formatDateTime },
    {
      title: "Dro",
      dataIndex: "endedAt",
      width: 190,
      render: (value?: string, row?: VisitRow) => (row?.status === "open" ? <Tag color="green">Pagaende</Tag> : formatDateTime(value)),
    },
    { title: "Hvor lenge", width: 140, render: (_, row) => visitDuration(row) },
    { title: "Inn", dataIndex: "enterSource", width: 150 },
    { title: "Ut", width: 150, render: (_, row) => (row.status === "open" ? "-" : row.leaveSource || "-") },
  ];

  const occupancyColumns: ColumnsType<VisitDisplayRow> = [
    { title: "Sted", dataIndex: "waypointName", fixed: "left", width: 210 },
    { title: "Kategori", dataIndex: "category", width: 130, render: categoryTag },
    { title: "Kom", dataIndex: "startedAt", width: 190, render: formatDateTime },
    {
      title: "Dro",
      dataIndex: "endedAt",
      width: 190,
      render: (value?: string, row?: VisitDisplayRow) => (row?.status === "open" ? <Tag color="green">Pagaende</Tag> : formatDateTime(value)),
    },
    { title: "Hvor lenge", width: 130, render: (_, row) => visitDuration(row) },
    { title: "Status", dataIndex: "status", width: 110, render: statusTag },
    { title: "Adresse", dataIndex: "address", ellipsis: true },
    { title: "Kilder", width: 180, render: (_, row) => [row.enterSource, row.leaveSource].filter(Boolean).join(" / ") || "-" },
  ];

  const occupancyCategoryColumns: ColumnsType<{ id: string; category: string; visits: number; totalDurationSeconds: number; openVisits: number }> = [
    { title: "Kategori", dataIndex: "category" },
    { title: "Besok", dataIndex: "visits", width: 90 },
    { title: "Aktiv", dataIndex: "openVisits", width: 90 },
    { title: "Total tid", dataIndex: "totalDurationSeconds", width: 130, render: durationSecondsLabel },
  ];

  const placeListColumns: ColumnsType<ZoneSummaryRow> = [
    {
      title: "Sted",
      dataIndex: "waypointName",
      render: (value: string, row) => (
        <div className="place-list-name">
          <strong>{value}</strong>
          <span>{row.waypoint?.address || row.topic}</span>
        </div>
      ),
    },
    {
      title: "Kategori",
      width: 120,
      render: (_, row) => categoryTag(row.waypoint?.category),
    },
    {
      title: "Status",
      width: 110,
      render: (_, row) => placeStatusTag(row),
    },
    {
      title: "Tid",
      dataIndex: "totalDuration",
      width: 110,
      render: durationOrDash,
    },
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
    { title: "Kategori", dataIndex: "category", render: categoryTag },
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
      render: (_, row) => (
        <Space size={6}>
          <Button size="small" icon={<EditOutlined />} onClick={() => openWaypointModal(undefined, row)}>
            Rediger
          </Button>
          <Popconfirm title="Deaktiver sone?" okText="Deaktiver" cancelText="Avbryt" onConfirm={() => void disableWaypoint(row)}>
            <Button size="small" danger icon={<PoweroffOutlined />} loading={waypointMutatingId === row.id}>
              Av
            </Button>
          </Popconfirm>
        </Space>
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
    { title: "Posisjonstid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Mottatt", dataIndex: "receivedAt", render: formatDateTime },
    { title: "Enhet", dataIndex: "topic" },
    { title: "Type", dataIndex: "messageType" },
    { title: "Event", dataIndex: "event", render: eventTag },
    { title: "Opprinnelse", width: 120, render: (_, row) => originTag(row) },
    { title: "Beregning", width: 120, render: (_, row) => calculationUseTag(row) },
    { title: "Posisjon", render: (_, row) => mapLink(row.lat, row.lon) },
    { title: "Fra forrige", dataIndex: "distanceFromPreviousM", width: 120, render: (value?: number | null) => (value == null ? "-" : `${formatNumber(value, 1)} m`) },
    { title: "Presisjon", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Batteri", dataIndex: "batteryPercent", render: (value?: number) => (value == null ? "-" : `${formatNumber(value)} %`) },
  ];

  const groupedMessageColumns: ColumnsType<MessageGroupRow> = [
    { title: "Antall", dataIndex: "count", width: 80 },
    { title: "Posisjonstid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Forst mottatt", dataIndex: "firstReceivedAt", render: formatDateTime },
    { title: "Sist mottatt", dataIndex: "lastReceivedAt", render: formatDateTime },
    { title: "Enhet", dataIndex: "topic" },
    {
      title: "Typer",
      dataIndex: "messageTypes",
      render: (values?: string[]) => (values?.length ? <Space size={4} wrap>{values.map((value) => <Tag key={value}>{value}</Tag>)}</Space> : "-"),
    },
    {
      title: "Event",
      dataIndex: "events",
      render: (values?: string[]) => (values?.length ? <Space size={4} wrap>{values.map((value) => <span key={value}>{eventTag(value)}</span>)}</Space> : "-"),
    },
    { title: "Posisjon", render: (_, row) => mapLink(row.lat, row.lon) },
    { title: "Fra forrige", dataIndex: "distanceFromPreviousM", width: 120, render: (value?: number | null) => (value == null ? "-" : `${formatNumber(value, 1)} m`) },
    { title: "Beregning", width: 120, render: (_, row) => calculationUseTag(row) },
    { title: "Presisjon", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Batteri sist", dataIndex: "batteryPercent", render: (value?: number) => (value == null ? "-" : `${formatNumber(value)} %`) },
  ];

  const eventColumns: ColumnsType<EventRow> = [
    { title: "Tid", dataIndex: "timestamp", render: formatDateTime },
    { title: "Sone", dataIndex: "waypointName" },
    { title: "Hendelse", dataIndex: "eventType", render: eventTag },
    { title: "Opprinnelse", width: 120, render: (_, row) => originTag(row) },
    { title: "Statusbruk", width: 130, render: (_, row) => stateUseTag(row) },
    { title: "Kilde", dataIndex: "sourceMessageType" },
    { title: "Posisjon", render: (_, row) => mapLink(row.lat, row.lon) },
    { title: "Presisjon", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
    { title: "Forklaring", dataIndex: "ignoredReason", ellipsis: true },
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
    { title: "Beregning", width: 120, render: (_, row) => calculationUseTag(row) },
    { title: "Presisjon", dataIndex: "accuracyM", render: (value?: number) => `${formatNumber(value)} m` },
  ];

  const buildColumns: ColumnsType<Record<string, any>> = [
    { title: "Build", dataIndex: "build", width: 90 },
    { title: "Dato", dataIndex: "date", width: 130 },
    { title: "Overskrift", dataIndex: "headline", width: 260 },
    { title: "Endringer", dataIndex: "changes", render: (changes?: string[]) => (changes || []).map((change) => <div key={change}>{change}</div>) },
  ];

  function handleTimePresetChange(value: string) {
    if (value === "custom") {
      setTimeFilterMode("custom");
      if (!customStart || !customEnd) {
        const end = new Date();
        const start = new Date(end.getTime() - 2 * 60 * 60 * 1000);
        setCustomStart(formatDateTimeLocalInput(start));
        setCustomEnd(formatDateTimeLocalInput(end));
      }
      return;
    }
    setTimeFilterMode("relative");
    setHours(value);
  }

  const controls = (
    <Space wrap className="time-filter-controls">
      <Select
        value={timeFilterMode === "custom" ? "custom" : hours}
        onChange={handleTimePresetChange}
        className="time-filter-select"
        options={[
          { value: "6", label: "Siste 6 timer" },
          { value: "12", label: "Siste 12 timer" },
          { value: "24", label: "Siste 24 timer" },
          { value: "168", label: "Siste 7 dager" },
          { value: "720", label: "Siste 30 dager" },
          { value: "0", label: "Alt" },
          { value: "custom", label: "Egendefinert" },
        ]}
      />
      {timeFilterMode === "custom" ? (
        <Space.Compact className="time-range-inputs">
          <Input aria-label="Fra tidspunkt" type="datetime-local" value={customStart} onChange={(event) => setCustomStart(event.target.value)} />
          <Input aria-label="Til tidspunkt" type="datetime-local" value={customEnd} onChange={(event) => setCustomEnd(event.target.value)} />
        </Space.Compact>
      ) : null}
      <Select
        value={categoryFilter}
        onChange={setCategoryFilter}
        className="category-filter-select"
        options={categoryFilterOptions}
      />
      <Button icon={<ToolOutlined />} loading={rebuilding} onClick={rebuildVisits}>
        Bygg sonebesok
      </Button>
      <Button type="primary" icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>
        Oppdater
      </Button>
    </Space>
  );

  function placeStatusTag(row: ZoneSummaryRow) {
    if (row.openVisits > 0 || row.lastStatus === "open") return <Tag color="green">Paa stedet</Tag>;
    if (row.lastStatus === "inside") return <Tag color="blue">Sist inne</Tag>;
    if (row.lastStatus === "closed" || row.lastStatus === "outside") return <Tag>Ute</Tag>;
    return <Tag color="gold">Ukjent</Tag>;
  }

  function openPlaceDetail(row: ZoneSummaryRow) {
    setSelectedPlaceId(placeKey(row.topic, row.waypointName));
  }

  const dashboard = useMemo(
    () => (
      <>
        <SectionHeader title="Dashboard" subtitle={health?.public.publishUrl || "OwnTracks HTTP-mottak"} />
        <Alert className="page-alert" type="info" showIcon message="Presisjonsfilter" description={precisionPolicyText} />
        <Row gutter={[12, 12]} className="metric-row">
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Status" value={health?.status || "-"} subtitle={health?.database === "ok" ? "Database OK" : "Database ukjent"} tone="#15803d" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Aktiv sone" value={filteredActiveVisits.length} subtitle={activeZoneNames} tone="#15803d" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Sonetid" value={durationSecondsLabel(occupancyTotalSeconds)} subtitle={`${filteredVisits.length} besok, ${timeFilterLabel}`} tone="#7c3aed" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Kartpunkter" value={mapLocations.length} subtitle={`${ignoredForAccuracy} ignorert i beregning`} tone="#0891b2" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Siste brukte posisjon" value={formatDateTime(latestUsableLocation?.timestamp || latestUsableLocation?.receivedAt)} subtitle={latestUsableLocation?.topic || "Ingen posisjon"} tone="#0891b2" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Presisjonsfilter" value={`${formatNumber(maxCalculationAccuracyM)} m`} subtitle={`Raadata beholdt: ${locations.length}`} tone="#475569" />
          </Col>
        </Row>
        <Row gutter={[12, 12]}>
          <Col xs={24} xl={15}>
            <Card title="Kart og siste spor" extra={<Typography.Text type="secondary">{mapLocations.length} av {locations.length} posisjoner brukes</Typography.Text>}>
              <OwnTracksMap data={filteredMapData} />
            </Card>
          </Col>
          <Col xs={24} xl={9}>
            <Card title="Siste sonebesok">
              <DataTable<VisitDisplayRow> columns={visitColumns.slice(0, 5) as ColumnsType<VisitDisplayRow>} data={occupancyRows.slice(0, 8)} />
            </Card>
          </Col>
        </Row>
      </>
    ),
    [activeZoneNames, filteredActiveVisits.length, filteredMapData, filteredVisits.length, health, ignoredForAccuracy, latestUsableLocation, locations.length, mapLocations.length, maxCalculationAccuracyM, occupancyRows, occupancyTotalSeconds, precisionPolicyText, timeFilterLabel, visitColumns],
  );

  let content: React.ReactNode = dashboard;
  if (view === "places") {
    content = (
      <>
        <SectionHeader
          title="Kjente steder"
          subtitle={`Opphold beregnet fra presise punkter. Periode: ${timeFilterLabel}`}
        />
        <Alert className="page-alert" type="info" showIcon message="Tydelig sonehistorikk" description={precisionPolicyText} />
        <div className="places-outlook-layout">
          <Card
            className="places-list-pane"
            title="Steder"
            extra={<Typography.Text type="secondary">{placeRows.length} stk</Typography.Text>}
          >
            <Table<ZoneSummaryRow>
              size="small"
              columns={placeListColumns}
              dataSource={placeRows}
              rowKey="id"
              pagination={false}
              scroll={{ y: "calc(100vh - 310px)", x: true }}
              rowClassName={(row) => (activePlace && placeKey(row.topic, row.waypointName) === placeKey(activePlace.topic, activePlace.waypointName) ? "place-list-row selected" : "place-list-row")}
              onRow={(row) => ({
                onClick: () => openPlaceDetail(row),
              })}
            />
          </Card>
          <div className="places-detail-pane">
            {activePlace ? (
              <>
                <Card
                  className="place-detail-header-card"
                  title={
                    <Space wrap>
                      <span>{activePlace.waypointName}</span>
                      {placeStatusTag(activePlace)}
                      {categoryTag(activePlace.waypoint?.category)}
                    </Space>
                  }
                  extra={
                    activePlace.waypoint ? (
                      <Button size="small" icon={<EditOutlined />} onClick={() => openWaypointModal(undefined, activePlace.waypoint)}>
                        Rediger waypoint
                      </Button>
                    ) : null
                  }
                >
                  <Row gutter={[10, 10]}>
                    <Col xs={24} md={8}>
                      <MetricCard title="Total tid" value={activePlace.totalDuration || "-"} subtitle={`${activePlace.visits} besok i perioden`} tone="#15803d" />
                    </Col>
                    <Col xs={24} md={8}>
                      <MetricCard title="Aktivt besok" value={activePlace.openVisits > 0 ? activePlace.currentDuration || "-" : "-"} subtitle={activePlace.openVisits > 0 ? `Fra ${formatDateTime(activePlace.currentStartedAt || activePlace.lastStartedAt)}` : "Ingen aktiv sone"} tone="#7c3aed" />
                    </Col>
                    <Col xs={24} md={8}>
                      <MetricCard title="Siste relevante leave" value={formatDateTime(activePlace.lastLeaveAt || activePlace.lastEndedAt)} subtitle={`Siste enter ${formatDateTime(activePlace.lastEnterAt || activePlace.lastStartedAt)}`} tone="#0891b2" />
                    </Col>
                  </Row>
                </Card>
                <Row gutter={[12, 12]}>
                  <Col xs={24} xl={10}>
                    <Card title="Kart" className="place-detail-map">
                      <OwnTracksMap data={selectedPlaceMapData} />
                    </Card>
                  </Col>
                  <Col xs={24} xl={14}>
                    <Card title="Besok" extra={<Typography.Text type="secondary">{selectedPlaceVisits.length} i valgt periode</Typography.Text>}>
                      <Table<VisitRow>
                        size="small"
                        columns={placeVisitColumns}
                        dataSource={selectedPlaceVisits}
                        rowKey="id"
                        pagination={{ pageSize: 20, showSizeChanger: false }}
                        scroll={{ x: true }}
                      />
                    </Card>
                  </Col>
                </Row>
              </>
            ) : (
              <Card>
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen kjente steder enda" />
              </Card>
            )}
          </div>
        </div>
      </>
    );
  } else if (view === "occupancy") {
    content = (
      <>
        <SectionHeader
          title="Opphold"
          subtitle={`Praktisk oversikt over hvor lenge du har vaert paa kjente steder. Periode: ${timeFilterLabel}`}
        />
        <Row gutter={[12, 12]} className="metric-row">
          <Col xs={24} md={8}>
            <MetricCard title="Total tid" value={durationSecondsLabel(occupancyTotalSeconds)} subtitle={`${occupancyRows.length} besok i valgt filter`} tone="#7c3aed" />
          </Col>
          <Col xs={24} md={8}>
            <MetricCard title="Aktive opphold" value={filteredActiveVisits.length} subtitle={activeZoneNames} tone="#15803d" />
          </Col>
          <Col xs={24} md={8}>
            <MetricCard title="Steder" value={placeRows.length} subtitle={categoryFilter === CATEGORY_ALL ? "Alle kategorier" : categoryFilter === CATEGORY_NONE ? "Uten kategori" : categoryFilter} tone="#0891b2" />
          </Col>
        </Row>
        <Row gutter={[12, 12]}>
          <Col xs={24} xl={8}>
            <Card title="Tid per kategori">
              <Table
                size="small"
                columns={occupancyCategoryColumns}
                dataSource={occupancyCategoryRows}
                rowKey="id"
                pagination={false}
              />
            </Card>
          </Col>
          <Col xs={24} xl={16}>
            <Card title="Opphold i perioden" extra={<Typography.Text type="secondary">{occupancyRows.length} rader</Typography.Text>}>
              <Table<VisitDisplayRow>
                size="small"
                columns={occupancyColumns}
                dataSource={occupancyRows}
                rowKey="id"
                pagination={{ pageSize: 25, showSizeChanger: false }}
                scroll={{ x: true }}
              />
            </Card>
          </Col>
        </Row>
      </>
    );
  } else if (view === "map") {
    content = (
      <>
        <SectionHeader
          title="Kart"
          subtitle={`${mapLocations.length} kartpunkter av ${locations.length} raapunkter, ${ignoredForAccuracy} ignorert over ${formatNumber(maxCalculationAccuracyM)} m - ${timeFilterLabel}`}
        />
        <Card title="Spor og soner">
          <OwnTracksMap data={filteredMapData} large />
        </Card>
      </>
    );
  } else if (view === "visits") {
    content = (
      <>
        <SectionHeader title="Sonebesok" subtitle="Oppsummering og siste beregnede/eventstyrte besok per waypoint" />
        <Row gutter={[12, 12]} className="metric-row">
          <Col xs={24} md={8}>
            <MetricCard title="Soner i perioden" value={placeRows.length} subtitle={`${filteredVisits.length} besok`} tone="#15803d" />
          </Col>
          <Col xs={24} md={8}>
            <MetricCard title="Total sonetid" value={durationSecondsLabel(occupancyTotalSeconds)} subtitle={timeFilterLabel} tone="#7c3aed" />
          </Col>
          <Col xs={24} md={8}>
            <MetricCard title="Apen naa" value={filteredActiveVisits.length} subtitle={activeZoneNames} tone="#f59e0b" />
          </Col>
        </Row>
        <Card title="Soneoppsummering" extra={<Typography.Text type="secondary">Sortert paa total tid</Typography.Text>}>
          <DataTable<ZoneSummaryRow> columns={zoneSummaryColumns} data={placeRows} rowKey="id" />
        </Card>
        <Card title="Siste sonebesok">
          <DataTable<VisitDisplayRow> columns={visitColumns as ColumnsType<VisitDisplayRow>} data={occupancyRows} />
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
            dataSource={filteredWaypoints}
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
        <SectionHeader title="Forslag" subtitle={`Mulige lokale soner basert paa stopp med presisjon maks ${formatNumber(maxCalculationAccuracyM)} m`} />
        <Card className="suggestion-control-card">
          <Space wrap>
            <Select
              value={suggestionHours}
              onChange={setSuggestionHours}
              options={[
                { value: "6", label: "Siste 6 timer" },
                { value: "12", label: "Siste 12 timer" },
                { value: "168", label: "Siste 7 dager" },
                { value: "720", label: "Siste 30 dager" },
                { value: "2160", label: "Siste 90 dager" },
                { value: "0", label: "Alt" },
              ]}
            />
            <InputNumber addonBefore="Min stopp" addonAfter="min" min={1} max={1440} value={suggestionMinMinutes} onChange={(value) => setSuggestionMinMinutes(Number(value || 10))} />
            <InputNumber addonBefore="Radius" addonAfter="m" min={15} max={500} value={suggestionRadiusM} onChange={(value) => setSuggestionRadiusM(Number(value || 80))} />
            <Tag color="blue">Presisjon maks {formatNumber(maxCalculationAccuracyM)} m</Tag>
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
        <SectionHeader title="Diagnose" subtitle={`Datakvalitet, rapporteringshull og beregningsgrunnlag. ${precisionPolicyText}`} />
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
            <MetricCard title="Presisjon p90" value={formatNumber(diagnostics?.accuracy.p90M)} suffix="m" subtitle={`Grense ${formatNumber(maxCalculationAccuracyM)} m`} tone="#0891b2" />
          </Col>
          <Col xs={24} md={8} xl={4}>
            <MetricCard title="Brukbare posisjoner" value={diagnostics?.counts.usableLocations ?? mapLocations.length} subtitle={`${ignoredForAccuracy} filtrert bort`} tone="#7c3aed" />
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
        <SectionHeader
          title="Meldinger"
          subtitle={`${locations.length} raameldinger / ${groupedMessages.length} posisjoner. ${ignoredForAccuracy} markert lav presisjon. Periode: ${timeFilterLabel}`}
        />
        <div className="message-view-toolbar">
          <Segmented
            value={messageView}
            onChange={(value) => setMessageView(value as "grouped" | "raw")}
            options={[
              { label: "Komprimert", value: "grouped" },
              { label: "Raadata", value: "raw" },
            ]}
          />
          <Typography.Text type="secondary">
            {messageView === "grouped"
              ? "Samler like posisjonstidspunkt og koordinater per enhet."
              : "Viser hver melding slik den er mottatt fra OwnTracks."}
          </Typography.Text>
        </div>
        {messageView === "grouped" ? (
          <DataTable<MessageGroupRow> columns={groupedMessageColumns} data={groupedMessages} />
        ) : (
          <DataTable<LocationRow> columns={locationColumns} data={[...locations].reverse()} />
        )}
      </>
    );
  } else if (view === "events") {
    content = (
      <>
        <SectionHeader title="Hendelser" subtitle={`Waypoint-definisjoner, enter og leave. Periode: ${timeFilterLabel}`} />
        <DataTable<EventRow> columns={eventColumns} data={filteredEvents} />
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
            <Col xs={24} md={12}>
              <Form.Item name="category" label="Kategori">
                <Select
                  allowClear
                  mode="tags"
                  placeholder="Eks. Hjem, Arbeid, Kunde, Familie"
                  options={categoryOptions}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
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
