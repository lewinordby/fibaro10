import {
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  StopOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Button, Card, Checkbox, DatePicker, Empty, Input, Segmented, Select, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import "dayjs/locale/nb";
import { useMemo, useState } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { fetchCarsDay, fetchCarsDayDetections, type CarsDayDetection, type CarsDayItem, type CarsDayParkingSession } from "../api";
import { ErrorBlock, LoadingBlock } from "../components/AsyncState";
import { PageHeader } from "../components/PageHeader";
import { PeriodNavigator } from "../components/PeriodNavigator";
import { useApiQuery } from "../hooks";
import { queryKeys } from "../queryKeys";
import "../styles/cars.css";

dayjs.locale("nb");

type PaymentFilter = "all" | "paid" | "unpaid";
type MinimumScore = 0 | 40 | 50 | 60 | 70 | 80 | 90;

const NORDIC_REGISTRY_COUNTRIES = new Set(["NO", "SE", "DK"]);

function isKnownOrFoundVehicle(item: CarsDayItem): boolean {
  const validation = item.registryValidation;
  const registryFound = validation.is_valid === true && (
    validation.local_match === true
    || NORDIC_REGISTRY_COUNTRIES.has(String(validation.country_code || "").toUpperCase())
  );
  return registryFound || item.knownInProtect || Boolean(item.vehicle);
}

function normalizedDay(value: string | null): string {
  const parsed = value ? dayjs(value) : dayjs();
  return parsed.isValid() ? parsed.format("YYYY-MM-DD") : dayjs().format("YYYY-MM-DD");
}

function timeLabel(value?: string | null): string {
  const parsed = value ? dayjs(value) : null;
  return parsed?.isValid() ? parsed.format("HH:mm:ss") : "–";
}

function paymentTimeLabel(value: string | null | undefined, selectedDay: string): string {
  const parsed = value ? dayjs(value) : null;
  if (!parsed?.isValid()) return "–";
  return parsed.format("YYYY-MM-DD") === selectedDay ? parsed.format("HH:mm") : parsed.format("DD.MM HH:mm");
}

function amountLabel(value: number): string {
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 }).format(value || 0);
}

function durationLabel(value?: number | null): string {
  if (value == null || value <= 0) return "";
  if (value < 60) return `${Math.round(value)} min`;
  const hours = Math.floor(value / 60);
  const minutes = Math.round(value % 60);
  return minutes ? `${hours} t ${minutes} min` : `${hours} t`;
}

function confidenceStatus(item: Pick<CarsDayItem, "averageUnifiScore" | "maximumUnifiScore">) {
  const score = item.maximumUnifiScore ?? item.averageUnifiScore;
  if (score != null && score >= 80) return { color: "success", label: "Høy", score: `Maks ${score}/100`, level: "high" };
  if (score != null && score >= 60) return { color: "warning", label: "Middels", score: `Maks ${score}/100`, level: "medium" };
  if (score != null) return { color: "error", label: "Lav", score: `Maks ${score}/100`, level: "low" };
  return { color: "default", label: "Ukjent", score: "Score mangler", level: "unscored" };
}

function registryStatus(item: CarsDayItem) {
  const validation = item.registryValidation;
  if (item.isLikelyOcrVariant) {
    return { color: "warning", label: `Mulig variant av ${item.likelyCanonicalPlate}`, detail: "Markert av Protect Ledger" };
  }
  if (validation.is_valid === true) {
    return {
      color: "success",
      label: validation.country || (validation.local_match ? "Lokalt bekreftet" : "Bekreftet"),
      detail: [validation.source, validation.vehicle_label].filter(Boolean).join(" · ") || validation.message,
    };
  }
  if (validation.likely_misread) {
    return { color: "error", label: "Sannsynlig feillesing", detail: validation.message };
  }
  return {
    color: validation.status === "error" ? "warning" : "processing",
    label: validation.status === "error" ? "Oppslag utsatt" : "Valideres",
    detail: validation.error || validation.message,
  };
}

function paymentStatus(item: CarsDayItem) {
  if (item.paymentStatus === "paid_same_day") {
    const wait = durationLabel(item.minutesBeforeFirstPayment);
    const detail = wait
      ? `Første betaling ${wait} etter første observasjon`
      : item.coveredDetectionCount
        ? `${item.coveredDetectionCount} observasjon${item.coveredDetectionCount === 1 ? "" : "er"} i betalt tidsrom`
        : "Betaling registrert samme kalenderdag";
    return { color: "success", icon: <CheckCircleOutlined />, label: "Dagsmatch · betalt", detail };
  }
  return { color: "error", icon: <StopOutlined />, label: "Ingen betalt økt", detail: item.hasParkingSession ? "Kun økt uten registrert beløp" : "Ingen parkering funnet" };
}

function sortedPaymentSessions(sessions: CarsDayParkingSession[]): CarsDayParkingSession[] {
  return [...sessions].sort((left, right) => String(left.startAt || "").localeCompare(String(right.startAt || "")));
}

function PaymentSessions({ sessions, selectedDay }: { sessions: CarsDayParkingSession[]; selectedDay: string }) {
  if (!sessions.length) return <span className="cars-muted">–</span>;
  return (
    <div className="cars-payment-list">
      {sortedPaymentSessions(sessions).map((session) => (
        <div className="cars-payment-time" key={session.id}>
          <strong>{paymentTimeLabel(session.startAt, selectedDay)}–{paymentTimeLabel(session.endAt, selectedDay)}</strong>
          <span>{amountLabel(session.amountKr)} kr{session.source ? ` · ${session.source}` : ""}</span>
        </div>
      ))}
    </div>
  );
}

function PaymentOverview({ item, selectedDay }: { item: CarsDayItem; selectedDay: string }) {
  const status = paymentStatus(item);
  const sessions = sortedPaymentSessions(item.paidSessions);
  return (
    <div className="cars-payment-overview">
      <div className="cars-payment-status">
        <Tag color={status.color} icon={status.icon}>{status.label}</Tag>
        <small>{status.detail}</small>
      </div>
      {sessions.map((session) => (
        <div className="cars-payment-window" key={session.id}>
          <div>
            <span>Betalt fra</span>
            <strong>{paymentTimeLabel(session.startAt, selectedDay)}</strong>
          </div>
          <div>
            <span>Betalt til</span>
            <strong>{paymentTimeLabel(session.endAt, selectedDay)}</strong>
          </div>
          <small>{amountLabel(session.amountKr)} kr{session.source ? ` · ${session.source}` : ""}</small>
        </div>
      ))}
    </div>
  );
}

function sortedDetections(detections: CarsDayDetection[]): CarsDayDetection[] {
  return [...detections].sort((left, right) => String(left.occurredAt || "").localeCompare(String(right.occurredAt || "")));
}

function RegistrationSnapshot({
  detection,
  fallbackAt,
  label,
  plate,
}: {
  detection?: CarsDayDetection;
  fallbackAt?: string | null;
  label: string;
  plate: string;
}) {
  const occurredAt = detection?.occurredAt || fallbackAt;
  const camera = detection?.cameraName || detection?.cameraId || "Ukjent kamera";
  const waitingForImage = detection?.snapshotStatus === "pending" || detection?.snapshotStatus === "capturing";
  return (
    <article className="cars-registration-card">
      <div className="cars-registration-heading">
        <span>{label}</span>
        <strong>{timeLabel(occurredAt)}</strong>
      </div>
      {detection?.snapshotUrl ? (
        <a
          className="cars-registration-image-link"
          href={detection.snapshotUrl}
          target="_blank"
          rel="noreferrer"
          aria-label={`Åpne ${label.toLocaleLowerCase("nb-NO")} av ${plate} i full størrelse`}
        >
          <img
            src={detection.snapshotUrl}
            alt={`${label} av ${plate} klokken ${timeLabel(occurredAt)}`}
            loading="lazy"
            decoding="async"
            fetchPriority="low"
          />
          <span>Åpne bilde</span>
        </a>
      ) : (
        <div className="cars-registration-image-empty">
          <CameraOutlined />
          <span>{waitingForImage ? "Henter bilde" : "Bilde mangler"}</span>
        </div>
      )}
      <Tooltip title={camera}>
        <small><CameraOutlined /> {camera}</small>
      </Tooltip>
    </article>
  );
}

function RegistrationOverview({ item }: { item: CarsDayItem }) {
  const detections = sortedDetections(item.detections);
  const first = detections[0];
  const last = detections[detections.length - 1];
  return (
    <div className="cars-registration-overview">
      <div className="cars-registration-pair">
        <RegistrationSnapshot detection={first} fallbackAt={item.firstDetectedAt} label="Første registrering" plate={item.plate} />
        <RegistrationSnapshot detection={last} fallbackAt={item.lastDetectedAt} label="Siste registrering" plate={item.plate} />
      </div>
      <small>{item.detectionCount} observasjon{item.detectionCount === 1 ? "" : "er"} denne dagen</small>
    </div>
  );
}

function DetectionDetails({ item, selectedDay }: { item: CarsDayItem; selectedDay: string }) {
  const { data, error, loading } = useApiQuery(
    queryKeys.carsDayDetections(selectedDay, item.plate),
    () => fetchCarsDayDetections(selectedDay, item.plate),
    { staleTime: selectedDay === dayjs().format("YYYY-MM-DD") ? 20_000 : 30 * 60_000 },
  );
  const detections = data?.detections ?? item.detections;
  return (
    <div className="cars-detection-details">
      <div className="cars-detail-heading">
        <div>
          <strong>Hele dagen for {item.plate}</strong>
          <span>{data?.detectionCount ?? item.detectionCount} kameraobservasjon{(data?.detectionCount ?? item.detectionCount) === 1 ? "" : "er"}</span>
        </div>
        <PaymentSessions sessions={item.paidSessions} selectedDay={selectedDay} />
      </div>
      <div className="cars-detection-grid">
        {loading && !data ? <Typography.Text type="secondary">Henter alle kameraobservasjonene â€¦</Typography.Text> : null}
        {error && !data ? <Typography.Text type="danger">Kunne ikke hente hele deteksjonslisten: {error.message}</Typography.Text> : null}
        {detections.map((detection, index) => (
          <div className="cars-detection-item" key={detection.recognitionId ?? `${detection.occurredAt}-${index}`}>
            <EyeOutlined />
            <strong>{timeLabel(detection.occurredAt)}</strong>
            <span>{detection.cameraName || detection.cameraId || "Ukjent kamera"}</span>
            {detection.observedPlate && detection.observedPlate !== item.plate ? <Tag color="warning">Lest {detection.observedPlate}</Tag> : null}
            <Tooltip title="UniFi Protects sikkerhet for objektdeteksjonen, ikke en garanti for hvert tegn i skiltet.">
              <Tag bordered={false} color={detection.unifiScore == null ? "default" : detection.unifiScore >= 80 ? "success" : detection.unifiScore >= 60 ? "warning" : "error"}>
                {detection.unifiScore == null ? "Ingen score" : `${detection.unifiScore}/100`}
              </Tag>
            </Tooltip>
            {detection.snapshotUrl ? (
              <>
                <a href={detection.snapshotUrl} target="_blank" rel="noreferrer">Deteksjonsbilde</a>
                <Tooltip title={`Bildet er hentet fra kameraet i webhooken. Beregnet tidsavvik mot OCR: ${detection.snapshotTimeOffsetMs == null ? "ukjent" : `${detection.snapshotTimeOffsetMs >= 0 ? "+" : ""}${(detection.snapshotTimeOffsetMs / 1000).toFixed(2)} s`}.`}>
                  <Tag bordered={false} color={detection.snapshotTimeOffsetMs == null ? "default" : Math.abs(detection.snapshotTimeOffsetMs) <= 1500 ? "success" : "warning"}>
                    {detection.snapshotTimeOffsetMs == null ? "Bildetid ukjent" : `Bilde ${detection.snapshotTimeOffsetMs >= 0 ? "+" : ""}${(detection.snapshotTimeOffsetMs / 1000).toFixed(2)} s`}
                  </Tag>
                </Tooltip>
              </>
            ) : (
              <small>{detection.snapshotStatus === "pending" || detection.snapshotStatus === "capturing" ? "Henter deteksjonsbilde" : "Uten deteksjonsbilde"}</small>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CarsPage() {
  const { view = "oversikt" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedDay = normalizedDay(searchParams.get("day"));
  const [query, setQuery] = useState("");
  const [paymentFilter, setPaymentFilter] = useState<PaymentFilter>("all");
  const [registryOnly, setRegistryOnly] = useState(false);
  const [minimumScore, setMinimumScore] = useState<MinimumScore>(0);
  const { data, error, loading, fetching, refetch } = useApiQuery(
    queryKeys.carsDay(selectedDay),
    () => fetchCarsDay(selectedDay),
    {
      staleTime: 0,
      refetchOnMount: "always",
      refetchOnWindowFocus: "always",
      refetchOnReconnect: "always",
      refetchInterval: selectedDay === dayjs().format("YYYY-MM-DD") ? 30_000 : false,
    },
  );

  const setDay = (value: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("day", value);
    setSearchParams(next);
  };

  const filteredItems = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("nb-NO");
    return (data?.items ?? []).filter((item) => {
      if (paymentFilter === "paid" && !item.hasPaidSession) return false;
      if (paymentFilter === "unpaid" && item.hasPaidSession) return false;
      if (registryOnly && !isKnownOrFoundVehicle(item)) return false;
      const highestScore = item.maximumUnifiScore ?? item.averageUnifiScore;
      if (minimumScore > 0 && (highestScore == null || highestScore < minimumScore)) return false;
      if (!needle) return true;
      const haystack = [
        item.plate,
        item.displayValue,
        item.vehicle?.name,
        item.vehicle?.area,
        item.vehicle?.title,
        item.registryValidation.country,
        item.registryValidation.source,
        item.registryValidation.vehicle_label,
        ...item.observedPlateValues,
        ...item.cameraNames,
      ].filter(Boolean).join(" ").toLocaleLowerCase("nb-NO");
      return haystack.includes(needle);
    });
  }, [data?.items, minimumScore, paymentFilter, query, registryOnly]);

  const columns = useMemo<ColumnsType<CarsDayItem>>(() => [
    {
      title: "Bil og kvalitet",
      dataIndex: "plate",
      width: 230,
      sorter: (left, right) => left.plate.localeCompare(right.plate, "nb"),
      filters: [
        {
          text: "Registerkontroll",
          value: "registry",
          children: [
            { text: "Bekreftet", value: "registry:valid" },
            { text: "Sannsynlig feillesing", value: "registry:likely_misread" },
            { text: "Venter / utsatt", value: "registry:pending_review" },
          ],
        },
        {
          text: "AI-sikkerhet",
          value: "confidence",
          children: [
            { text: "Høy", value: "confidence:high" },
            { text: "Middels", value: "confidence:medium" },
            { text: "Lav", value: "confidence:low" },
            { text: "Uten score", value: "confidence:unscored" },
          ],
        },
      ],
      onFilter: (value, item) => {
        const [kind, selected] = String(value).split(":", 2);
        if (kind === "registry") return item.presentationStatus === selected;
        if (kind === "confidence") return confidenceStatus(item).level === selected;
        return true;
      },
      render: (_, item) => {
        const registry = registryStatus(item);
        const confidence = confidenceStatus(item);
        const vehicleLabel = item.vehicle?.title || item.vehicle?.name || item.registryValidation.vehicle_label || (item.knownInProtect ? "Kjent i Protect" : "Ikke i kjøretøyregister");
        return (
          <div className="cars-vehicle-cell">
            <div className="cars-plate-cell">
              {item.vehicle?.path ? <Link to={item.vehicle.path}>{item.plate}</Link> : <strong>{item.plate}</strong>}
              <span>{vehicleLabel}</span>
              {item.vehicle?.area ? <small>{item.vehicle.area}</small> : null}
            </div>
            <div className="cars-quality-row">
              <Tooltip title={registry.detail}>
                <Tag color={registry.color} icon={item.likelyMisread ? <WarningOutlined /> : <SafetyCertificateOutlined />}>{registry.label}</Tag>
              </Tooltip>
              <Tooltip title={`Høyeste UniFi-score for objektdeteksjonen. Gjennomsnitt ${item.averageUnifiScore ?? "mangler"}/100. ${item.matchingReadCount} like avlesninger, ${item.scoredDetectionCount} med score.`}>
                <Tag color={confidence.color}>{confidence.label} · {confidence.score}</Tag>
              </Tooltip>
              {item.mergedVariantCount ? <Tag color="warning">{item.mergedVariantCount} OCR-variant samlet</Tag> : null}
              {item.ocrWarning && !item.mergedVariantCount ? (
                <Tooltip title={`Nesten like skilt: ${item.ocrVariantCandidates.map((candidate) => candidate.plate).join(", ")}`}>
                  <Tag color="warning">Mulig OCR-variant</Tag>
                </Tooltip>
              ) : null}
            </div>
            <Tooltip title={item.cameraNames.join(", ") || "Ukjent kamera"}>
              <span className="cars-camera-summary"><CameraOutlined /> {item.cameraNames.join(", ") || "Ukjent kamera"}</span>
            </Tooltip>
          </div>
        );
      },
    },
    {
      title: "Første og siste registrering",
      key: "registrationOverview",
      width: 450,
      sorter: (left, right) => String(left.firstDetectedAt || "").localeCompare(String(right.firstDetectedAt || "")),
      render: (_, item) => <RegistrationOverview item={item} />,
    },
    {
      title: "Betalt fra / til",
      dataIndex: "paymentStatus",
      width: 250,
      filters: [
        { text: "Betalt samme dag", value: "paid_same_day" },
        { text: "Ingen betaling", value: "no_payment" },
      ],
      onFilter: (value, item) => item.paymentStatus === value,
      render: (_, item) => <PaymentOverview item={item} selectedDay={selectedDay} />,
    },
  ], [selectedDay]);

  if (view !== "oversikt") return <Navigate to={`/biler/oversikt?day=${selectedDay}`} replace />;
  if (loading && !data) return <LoadingBlock />;
  if (error && !data) return <ErrorBlock error={error} />;

  const summary = data?.summary ?? { uniquePlates: 0, detections: 0, paidPlates: 0, coveredPlates: 0, withoutPayment: 0, mergedOcrVariants: 0, scoredDetections: 0, lowConfidencePlates: 0, ocrWarningPlates: 0, reviewPlates: 0, validatedPlates: 0, likelyMisreads: 0, pendingValidation: 0 };
  const selectedDayValue = dayjs(selectedDay);
  const observationWindowLabel = data?.observationWindow.firstDetectedAt
    ? `${timeLabel(data.observationWindow.firstDetectedAt)}–${timeLabel(data.observationWindow.lastDetectedAt)}`
    : "Ingen kameraobservasjoner";

  return (
    <div className="page-stack cars-page">
      <PageHeader
        eyebrow="UniFi Protect + parkering"
        title="Observerte biler"
        description="Én samlet dagsjournal per bil med alle kameraobservasjoner, OCR-varianter og betalinger i kronologisk sammenheng."
        actions={
          <Button icon={<ReloadOutlined spin={fetching} />} onClick={() => void refetch()} disabled={fetching}>
            Oppdater
          </Button>
        }
        meta={
          fetching
            ? <span className="cars-generated">Sammenstiller skilt og parkering …</span>
            : data?.generatedAt
              ? <span className="cars-generated">Sammenstilt {timeLabel(data.generatedAt)}</span>
              : null
        }
      />

      <Card className="cars-daybar">
        <div className="cars-daybar-label">
          <span>Valgt dag</span>
          <strong>{selectedDayValue.format("dddd D. MMMM YYYY")}</strong>
        </div>
        <PeriodNavigator
          previousLabel="Forrige"
          nextLabel="Neste"
          canNext={selectedDayValue.isBefore(dayjs(), "day")}
          onPrevious={() => setDay(data?.prevDay || selectedDayValue.subtract(1, "day").format("YYYY-MM-DD"))}
          onNext={() => setDay(data?.nextDay || selectedDayValue.add(1, "day").format("YYYY-MM-DD"))}
          middle={
            <DatePicker
              allowClear={false}
              format="DD.MM.YYYY"
              size="small"
              value={selectedDayValue}
              disabledDate={(current) => current.isAfter(dayjs(), "day")}
              onChange={(value) => value && setDay(value.format("YYYY-MM-DD"))}
            />
          }
          extra={<Button size="small" onClick={() => setDay(dayjs().format("YYYY-MM-DD"))}>I dag</Button>}
        />
      </Card>

      <Card className="cars-policy-card">
        <div className="cars-policy-icon"><CheckCircleOutlined /></div>
        <div>
          <strong>{data?.matchPolicy.label || "Samme bil og samme dag"}</strong>
          <span>{data?.matchPolicy.detail || "En betaling når som helst denne dagen gir dagsmatch."}</span>
        </div>
        <Tag icon={<ClockCircleOutlined />}>Kameradata {observationWindowLabel}</Tag>
      </Card>

      <div className="cars-summary-grid">
        <Card className="cars-summary-card tone-cars"><span>Unike biler</span><strong>{summary.uniquePlates}</strong><small>{summary.mergedOcrVariants} OCR-varianter samlet</small></Card>
        <Card className="cars-summary-card tone-cars"><span>Deteksjoner</span><strong>{summary.detections}</strong><small>Alle kameraobservasjoner</small></Card>
        <Card className="cars-summary-card tone-ok"><span>Registerbekreftet</span><strong>{summary.validatedPlates}</strong><small>Lokalt, Norge, Sverige eller Danmark</small></Card>
        <Card className="cars-summary-card tone-ok"><span>Dagsmatch betaling</span><strong>{summary.paidPlates}</strong><small>{summary.coveredPlates} også sett i betalt tidsrom</small></Card>
        <Card className="cars-summary-card tone-warn"><span>Uten betaling</span><strong>{summary.withoutPayment}</strong><small>Ingen betalt økt funnet</small></Card>
        <Card className="cars-summary-card tone-warn"><span>Trenger kontroll</span><strong>{summary.reviewPlates}</strong><small>{summary.likelyMisreads} mulig feillesing · {summary.pendingValidation} venter</small></Card>
      </div>

      <Card className="cars-list-card" title="Biler denne dagen" extra={`${filteredItems.length} av ${summary.uniquePlates}`}>
        <div className="cars-toolbar">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Søk reg.nr, navn, område eller kamera"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="cars-toolbar-controls">
            <Checkbox
              checked={registryOnly}
              onChange={(event) => setRegistryOnly(event.target.checked)}
            >
              Kun kjente eller registerfunnet
            </Checkbox>
            <Select<MinimumScore>
              aria-label="Minimum høyeste UniFi-score"
              title="Filtrerer på bilens høyeste UniFi-score denne dagen"
              className="cars-score-filter"
              value={minimumScore}
              onChange={setMinimumScore}
              options={[
                { label: "Alle scorer", value: 0 },
                { label: "Minst 40", value: 40 },
                { label: "Minst 50", value: 50 },
                { label: "Minst 60", value: 60 },
                { label: "Minst 70", value: 70 },
                { label: "Minst 80", value: 80 },
                { label: "Minst 90", value: 90 },
              ]}
            />
            <Segmented<PaymentFilter>
              value={paymentFilter}
              onChange={setPaymentFilter}
              options={[
                { label: "Alle", value: "all" },
                { label: "Med betaling", value: "paid" },
                { label: "Uten betaling", value: "unpaid" },
              ]}
            />
          </div>
        </div>
        <Table<CarsDayItem>
          className="cars-day-table"
          rowKey="plate"
          columns={columns}
          dataSource={filteredItems}
          loading={fetching && !data}
          size="small"
          tableLayout="fixed"
          pagination={{ pageSize: 50, showSizeChanger: true, pageSizeOptions: [25, 50, 100], showTotal: (total) => `${total} biler` }}
          expandable={{ expandedRowRender: (item) => <DetectionDetails item={item} selectedDay={selectedDay} />, rowExpandable: (item) => item.detectionCount > 0 }}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Ingen skilt detektert denne dagen" /> }}
        />
        <Typography.Text className="cars-table-note" type="secondary">
          Dagsmatch betyr at samme validerte bil har minst én betalt parkering som berører valgt kalenderdag. Tidspunktet brukes til å forklare forløpet, men avviser ikke en betaling selv om sjåføren ventet lenge. Protect Ledger beholder alle rålesinger; Fibaro10 samler en bekreftet OCR-variant under hovedskiltet og viser originalavlesningen i detaljene. Sammenstillingen bygges på nytt hver gang siden åpnes eller blir synlig igjen.
        </Typography.Text>
      </Card>
    </div>
  );
}
