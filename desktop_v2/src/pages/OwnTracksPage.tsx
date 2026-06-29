import { AimOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Segmented, Space, Tabs, Typography } from "antd";
import L from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  fetchModule,
  fetchOwnTracksMap,
  type ModuleResponse,
  type OwnTracksMapDevice,
  type OwnTracksMapLocation,
  type OwnTracksMapResponse,
  type OwnTracksMapWaypoint,
} from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { TableSearch } from "../components/TableSearch";
import { decimal } from "../format";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import { ModuleMetric } from "./module/ModuleMetric";
import { ModuleTablePane, tabLabel } from "./module/ModuleTablePane";

const DEFAULT_CENTER: [number, number] = [61.1153, 10.4662];
const TRACK_COLORS = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2", "#be123c"];
const MAP_LIMIT = 5000;

function displayName(value: { username?: string | null; device?: string | null; trackerId?: string | null; topic: string }) {
  return [value.username, value.device || value.trackerId].filter(Boolean).join(" / ") || value.topic;
}

function shortDateTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("nb-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function popupRows(rows: Array<[string, unknown]>) {
  return rows
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
}

function locationPopup(point: OwnTracksMapLocation) {
  return `<section class="owntracks-popup">
    <h4>${escapeHtml(displayName(point))}</h4>
    ${popupRows([
      ["Tid", shortDateTime(point.timestamp || point.receivedAt)],
      ["Type", point.messageType],
      ["Event", point.event],
      ["Nøyaktighet", point.accuracyM != null ? `${decimal(point.accuracyM, 0)} m` : null],
      ["Batteri", point.batteryPercent != null ? `${point.batteryPercent}%` : null],
      ["Tilkobling", point.connection],
      ["Fart", point.velocityKmh != null ? `${decimal(point.velocityKmh, 1)} km/t` : null],
    ])}
  </section>`;
}

function devicePopup(device: OwnTracksMapDevice) {
  return `<section class="owntracks-popup">
    <h4>${escapeHtml(displayName(device))}</h4>
    ${popupRows([
      ["Sist sett", shortDateTime(device.lastSeenAt || device.lastReceivedAt)],
      ["Siste event", device.lastEvent],
      ["Type", device.lastMessageType],
      ["Nøyaktighet", device.accuracyM != null ? `${decimal(device.accuracyM, 0)} m` : null],
      ["Batteri", device.batteryPercent != null ? `${device.batteryPercent}%` : null],
      ["Tilkobling", device.connection],
    ])}
  </section>`;
}

function waypointPopup(waypoint: OwnTracksMapWaypoint) {
  return `<section class="owntracks-popup">
    <h4>${escapeHtml(waypoint.name)}</h4>
    ${popupRows([
      ["Enhet", displayName(waypoint)],
      ["Status", waypoint.state],
      ["Sist sett", shortDateTime(waypoint.lastSeenAt || waypoint.lastEventAt)],
      ["Radius", waypoint.radiusM != null ? `${decimal(waypoint.radiusM, 0)} m` : null],
      ["Nøyaktighet", waypoint.accuracyM != null ? `${decimal(waypoint.accuracyM, 0)} m` : null],
    ])}
  </section>`;
}

function topicColor(topic: string, index: number) {
  let hash = 0;
  for (const char of topic) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return TRACK_COLORS[(hash + index) % TRACK_COLORS.length];
}

function OwnTracksMap({ data }: { data: OwnTracksMapResponse }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: DEFAULT_CENTER,
      zoom: 13,
      zoomControl: true,
      preferCanvas: true,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (layerRef.current) {
      layerRef.current.remove();
      layerRef.current = null;
    }

    const root = L.layerGroup().addTo(map);
    layerRef.current = root;
    const bounds = L.latLngBounds([]);
    const byTopic = new Map<string, OwnTracksMapLocation[]>();
    data.locations.forEach((point) => {
      if (!Number.isFinite(point.lat) || !Number.isFinite(point.lon)) return;
      const items = byTopic.get(point.topic) ?? [];
      items.push(point);
      byTopic.set(point.topic, items);
    });

    Array.from(byTopic.entries()).forEach(([topic, points], index) => {
      const color = topicColor(topic, index);
      const latLngs = points.map((point) => L.latLng(point.lat, point.lon));
      if (latLngs.length >= 2) {
        L.polyline(latLngs, { color, weight: 3, opacity: 0.55 }).addTo(root);
      }
      points.forEach((point) => {
        const marker = L.circleMarker([point.lat, point.lon], {
          radius: 3,
          color,
          fillColor: color,
          fillOpacity: 0.58,
          weight: 1,
        }).bindPopup(locationPopup(point));
        marker.addTo(root);
        bounds.extend([point.lat, point.lon]);
      });
    });

    data.waypoints.forEach((waypoint) => {
      if (!Number.isFinite(waypoint.lat) || !Number.isFinite(waypoint.lon)) return;
      const color = waypoint.isInside ? "#16a34a" : "#64748b";
      if (waypoint.radiusM && waypoint.radiusM > 0) {
        L.circle([waypoint.lat, waypoint.lon], {
          radius: waypoint.radiusM,
          color,
          fillColor: color,
          fillOpacity: 0.08,
          weight: 1.4,
        }).addTo(root);
      }
      L.circleMarker([waypoint.lat, waypoint.lon], {
        radius: 7,
        color,
        fillColor: "#ffffff",
        fillOpacity: 0.95,
        weight: 2,
      })
        .bindPopup(waypointPopup(waypoint))
        .addTo(root);
      bounds.extend([waypoint.lat, waypoint.lon]);
    });

    data.devices.forEach((device, index) => {
      if (!Number.isFinite(device.lat) || !Number.isFinite(device.lon)) return;
      const color = topicColor(device.topic, index);
      const marker = L.marker([device.lat, device.lon], {
        icon: L.divIcon({
          className: "owntracks-device-marker",
          html: `<span style="--marker-color:${color}">${escapeHtml(device.trackerId || device.device || "OT")}</span>`,
          iconSize: [44, 28],
          iconAnchor: [22, 28],
        }),
      }).bindPopup(devicePopup(device));
      marker.addTo(root);
      bounds.extend([device.lat, device.lon]);
    });

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [36, 36], maxZoom: 17 });
    } else {
      map.setView(DEFAULT_CENTER, 13);
    }
  }, [data]);

  return <div className="owntracks-map" ref={containerRef} />;
}

function OwnTracksTables({ data }: { data: ModuleResponse }) {
  const [query, setQuery] = useState("");
  const [draftQuery, setDraftQuery] = useState("");

  function runSearch(value = draftQuery) {
    setQuery(value.trim());
  }

  function clearSearch() {
    setDraftQuery("");
    setQuery("");
  }

  if (!data.tables.length) return null;
  return (
    <Card className="table-card module-table-card">
      <TableSearch
        placeholder="Søk i OwnTracks-tabellene"
        value={draftQuery}
        onValueChange={setDraftQuery}
        onClear={clearSearch}
        onSearch={runSearch}
      />
      <Tabs
        items={data.tables.map((table) => ({
          key: table.title,
          label: tabLabel(table, query),
          children: <ModuleTablePane table={table} query={query} />,
        }))}
      />
    </Card>
  );
}

export default function OwnTracksPage() {
  const [hours, setHours] = useState(24);
  const mapQuery = useApiQuery(queryKeys.ownTracksMap(hours, MAP_LIMIT), () => fetchOwnTracksMap(hours, MAP_LIMIT));
  const moduleQuery = useApiQuery(queryKeys.module("admin", "owntracks"), () => fetchModule("admin", "owntracks"));
  const generatedLabel = useMemo(() => shortDateTime(mapQuery.data?.generatedAt), [mapQuery.data?.generatedAt]);

  if (mapQuery.loading || moduleQuery.loading) return <LoadingBlock />;
  if (mapQuery.error || !mapQuery.data) return <ErrorBlock error={mapQuery.error} />;
  if (moduleQuery.error || !moduleQuery.data) return <ErrorBlock error={moduleQuery.error} />;

  return (
    <Space direction="vertical" size={14} className="page-stack owntracks-page">
      <Card
        className="owntracks-map-card"
        title={
          <Space size={10}>
            <AimOutlined />
            <span>OwnTracks kart</span>
          </Space>
        }
        extra={
          <Space size={10}>
            <Segmented
              size="small"
              value={hours}
              options={[
                { label: "1t", value: 1 },
                { label: "6t", value: 6 },
                { label: "24t", value: 24 },
                { label: "7d", value: 168 },
                { label: "Alle", value: 0 },
              ]}
              onChange={(value) => setHours(Number(value))}
            />
            <Button size="small" icon={<ReloadOutlined />} onClick={() => mapQuery.refetch()}>
              Oppdater
            </Button>
          </Space>
        }
      >
        <div className="owntracks-map-meta">
          <Typography.Text type="secondary">
            {mapQuery.data.locations.length} meldinger · {mapQuery.data.devices.length} enheter · {mapQuery.data.waypoints.length} waypoints
          </Typography.Text>
          <Typography.Text type="secondary">Sist oppdatert {generatedLabel}</Typography.Text>
        </div>
        <OwnTracksMap data={mapQuery.data} />
        <div className="owntracks-map-legend" aria-label="Kartforklaring">
          <span><i className="track" /> Spor og meldinger</span>
          <span><i className="device" /> Siste posisjon</span>
          <span><i className="waypoint" /> Waypoint</span>
        </div>
      </Card>

      {moduleQuery.data.cards.length ? (
        <div className="metric-grid primary-grid">
          {moduleQuery.data.cards.map((card) => (
            <ModuleMetric card={card} key={card.title} module="admin" view="owntracks" />
          ))}
        </div>
      ) : null}

      <OwnTracksTables data={moduleQuery.data} />
    </Space>
  );
}
