import { Button, Card, Select, Space, Typography } from "antd";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

type LegacySection = {
  group: string;
  items: Array<{ label: string; path: string }>;
};

const LEGACY_SECTIONS: LegacySection[] = [
  {
    group: "Status",
    items: [
      { label: "Dashboard", path: "/status/dashboard" },
      { label: "Nøkkeltall", path: "/status/nokkeltall" },
      { label: "Omsetning", path: "/status/omsetning" },
      { label: "Statistikk", path: "/status/statistikk" },
      { label: "Datakilder", path: "/status/datakilder" },
      { label: "Dagslinje", path: "/status/dagslinje" },
    ],
  },
  {
    group: "Parkering",
    items: [
      { label: "Oversikt", path: "/parkering/oversikt" },
      { label: "Parkeringer", path: "/parkering/parkeringer" },
      { label: "Kjøretøy", path: "/parkering/kjoretoy" },
      { label: "Bilstatistikk", path: "/parkering/bilstatistikk" },
      { label: "Område", path: "/parkering/omrade" },
      { label: "Prognose", path: "/parkering/prognose" },
      { label: "Navnoppslag", path: "/parkering/navn-oppslag" },
      { label: "Områdeoppslag", path: "/parkering/omrade-oppslag" },
    ],
  },
  {
    group: "Soling",
    items: [
      { label: "Oversikt", path: "/soling/oversikt" },
      { label: "Dagslinje", path: "/soling/dagslinje" },
      { label: "Detaljer", path: "/soling/detaljer" },
      { label: "Enkeltimer", path: "/soling/enkeltimer" },
      { label: "Senger", path: "/soling/senger" },
      { label: "Medlemmer", path: "/soling/medlemmer" },
      { label: "Prognose", path: "/soling/prognose" },
    ],
  },
  {
    group: "Energi",
    items: [
      { label: "Status", path: "/energi/status" },
      { label: "Kurser", path: "/energi/kurser" },
      { label: "Laster", path: "/energi/laster" },
      { label: "Forbruk per seng", path: "/energi/forbruk-per-seng" },
      { label: "Elvia", path: "/energi/elvia" },
    ],
  },
  {
    group: "Lys og ventilasjon",
    items: [
      { label: "Lys dagslogg", path: "/lys/dagslogg-lux" },
      { label: "Lys hendelser", path: "/lys/hendelser" },
      { label: "Lux logging", path: "/lys/lux-logging" },
      { label: "Lys innstillinger", path: "/lys/innstillinger" },
      { label: "Ventilasjon dagslogg", path: "/ventilasjon/dagslogg-temp" },
      { label: "Ventilasjon hendelser", path: "/ventilasjon/hendelser" },
      { label: "Temp logg", path: "/ventilasjon/temp-logg" },
      { label: "Yr logg", path: "/ventilasjon/yr-logg" },
      { label: "Ventilasjon innstillinger", path: "/ventilasjon/innstillinger" },
    ],
  },
  {
    group: "Renhold og admin",
    items: [
      { label: "Renhold oversikt", path: "/renhold/oversikt" },
      { label: "AI søk", path: "/ai/sok" },
      { label: "AI innstillinger", path: "/ai/innstillinger" },
      { label: "Konto", path: "/konto/oversikt" },
      { label: "Brukere og tilgang", path: "/konto/brukere-og-tilgang" },
      { label: "Build", path: "/konto/build" },
      { label: "Teknisk", path: "/konto/teknisk" },
      { label: "Manual", path: "/konto/manual" },
    ],
  },
];

const LEGACY_ITEMS = LEGACY_SECTIONS.flatMap((section) =>
  section.items.map((item) => ({ ...item, group: section.group })),
);

function normalizePath(value: string | null): string {
  const candidate = value && value.startsWith("/") && !value.startsWith("/v2") ? value : "/status/dashboard";
  return candidate;
}

export default function LegacyPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPath = normalizePath(searchParams.get("path"));
  const options = useMemo(
    () =>
      LEGACY_SECTIONS.map((section) => ({
        label: section.group,
        options: section.items.map((item) => ({ label: item.label, value: item.path })),
      })),
    [],
  );
  const selectedItem = LEGACY_ITEMS.find((item) => item.path === selectedPath);

  function setPath(path: string) {
    setSearchParams({ path });
  }

  return (
    <Space direction="vertical" size={14} className="page-stack legacy-page">
      <section className="section-head module-head">
        <div>
          <Typography.Text className="eyebrow">V1 klassisk UI</Typography.Text>
          <Typography.Title level={1}>{selectedItem?.label ?? "V1 side"}</Typography.Title>
          <Typography.Paragraph>{selectedItem?.group ?? "Gammelt grensesnitt i samme innlogging."}</Typography.Paragraph>
        </div>
        <Space>
          <Select className="legacy-select" value={selectedPath} options={options} onChange={setPath} />
          <Button href="/v1" target="_blank" rel="noreferrer">
            Åpne V1 i ny fane
          </Button>
          <Button href={selectedPath} target="_blank" rel="noreferrer">
            Åpne valgt side
          </Button>
        </Space>
      </section>
      <Card className="legacy-frame-card">
        <iframe title="Klassisk Fibaro10" src={selectedPath} className="legacy-frame" />
      </Card>
    </Space>
  );
}
