import { App as AntApp, Button, Card, Empty, Space, Tag, Tooltip, Typography } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { KobleQualifiedRow, KobleQualifiedSun2Row, KobleReviewCandidate, KobleReviewData } from "../../api";
import { updateKobleCandidate } from "../../api";
import "../../styles/koble.css";

const krFormatter = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 });
const numberFormatter = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 1 });
const dateTimeFormatter = new Intl.DateTimeFormat("nb-NO", {
  day: "2-digit",
  month: "2-digit",
  year: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});
const timeFormatter = new Intl.DateTimeFormat("nb-NO", { hour: "2-digit", minute: "2-digit" });

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return dateTimeFormatter.format(date);
}

function formatTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return timeFormatter.format(date);
}

function formatKr(value?: number | null): string {
  return `${krFormatter.format(Math.round(Number(value || 0)))} kr`;
}

function formatNumber(value?: number | null, suffix = ""): string {
  const numeric = Number(value || 0);
  return `${numberFormatter.format(numeric)}${suffix}`;
}

function formatPercent(value?: number | null): string {
  return `${numberFormatter.format(Number(value || 0))}%`;
}

function confidenceTone(candidate: KobleReviewCandidate): "success" | "warning" | "danger" {
  if (candidate.status === "Bekreftet") return "success";
  if (candidate.status === "Avvist") return "danger";
  if (candidate.confidence >= 85 && candidate.competitorMatchesCount === 0) return "success";
  if (candidate.confidence >= 70) return "warning";
  return "danger";
}

function statusColor(status: string): string {
  if (status === "Bekreftet") return "green";
  if (status === "Avvist") return "red";
  return "gold";
}

function candidateFlags(candidate: KobleReviewCandidate): string[] {
  const flags: string[] = [];
  if (candidate.plateCandidateCount > 1) flags.push(`${candidate.plateCandidateCount} SUN2-alternativer for bilen`);
  if (candidate.sun2CandidateCount > 1) flags.push(`${candidate.sun2CandidateCount} biler mot samme SUN2`);
  if (candidate.competitorMatchesCount > 0) flags.push(`beste konkurrent har ${candidate.competitorMatchesCount} treff`);
  if (!flags.length && candidate.confidence >= 85) flags.push("Ingen tydelig konkurranse");
  return flags;
}

function statusLabel(candidate: KobleReviewCandidate): string {
  if (candidate.status === "Bekreftet") return "Bekreftet kobling";
  if (candidate.status === "Avvist") return "Avvist kandidat";
  return candidate.confidence >= 85 ? "Klar for visuell kontroll" : "Krever ekstra kontroll";
}

function qualifiedRowKey(row: KobleQualifiedRow): string {
  return `${row.plate}-${row.sun2Id}-${row.id}`;
}

function qualifiedSun2RowKey(row: KobleQualifiedSun2Row): string {
  return `${row.sun2Id}-${row.plate}-${row.id}`;
}

export function KobleReviewPanel({
  review,
  view,
  onReload,
}: {
  review: KobleReviewData;
  view: string;
  onReload: () => Promise<unknown> | unknown;
}) {
  const { message, modal } = AntApp.useApp();
  const navigate = useNavigate();
  const [shown, setShown] = useState(10);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const visibleCandidates = useMemo(() => review.candidates.slice(0, shown), [review.candidates, shown]);
  const qualifiedRows = review.qualifiedRows ?? [];
  const qualifiedSun2Rows = review.qualifiedSun2Rows ?? [];
  const visibleQualifiedRows = qualifiedRows.slice(0, 12);
  const shownQualifiedRows = view === "biltreff" ? qualifiedRows : visibleQualifiedRows;
  const qualifiedSun2Count = useMemo(
    () => new Set(qualifiedSun2Rows.map((row) => row.sun2Id).filter(Boolean)).size,
    [qualifiedSun2Rows],
  );
  const hasCustomKobleView = view === "oversikt" || view === "biltreff" || view === "sun2" || view === "kandidater";

  async function setCandidateStatus(candidate: KobleReviewCandidate, status: "Bekreftet" | "Avvist") {
    if (updatingId) return;
    setUpdatingId(candidate.id);
    try {
      const result = await updateKobleCandidate(candidate.id, { status });
      message.success(String(result.message || "Kobling oppdatert"));
      await onReload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kobling kunne ikke oppdateres");
    } finally {
      setUpdatingId(null);
    }
  }

  function confirmCandidateStatus(candidate: KobleReviewCandidate, status: "Bekreftet" | "Avvist") {
    modal.confirm({
      title: status === "Bekreftet" ? "Bekreft kobling?" : "Avvis kandidat?",
      content:
        status === "Bekreftet"
          ? `Koble ${candidate.plate} til SUN2 ${candidate.sun2Id}.`
          : `Avvis kobling mellom ${candidate.plate} og SUN2 ${candidate.sun2Id}.`,
      okText: status,
      cancelText: "Avbryt",
      okButtonProps: { danger: status === "Avvist" },
      onOk: () => setCandidateStatus(candidate, status),
    });
  }

  async function copySun2(candidate: KobleReviewCandidate) {
    try {
      await navigator.clipboard.writeText(candidate.sun2Id);
      message.success(`SUN2 ${candidate.sun2Id} kopiert`);
    } catch {
      message.error("Kunne ikke kopiere SUN2-ID");
    }
  }

  if (!hasCustomKobleView) return null;

  return (
    <section className="koble-review">
      {view === "oversikt" ? (
      <Card className="work-card koble-review-intro">
        <div className="koble-review-intro-main">
          <Typography.Text className="koble-review-eyebrow">Koblingsmotor</Typography.Text>
          <Typography.Title level={3}>Parkering mot SUN2</Typography.Title>
          <Typography.Text type="secondary">
            Bruk undersidene til SUN2-kontroll, biltreff, kandidater, treffgrunnlag og jobbstatus.
          </Typography.Text>
        </div>
        <div className="koble-review-intro-stats">
          <span>
            <strong>{review.strongCandidateCount}</strong>
            sterke
          </span>
          <span>
            <strong>{review.candidateCount}</strong>
            kandidater
          </span>
          <span>
            <strong>{review.processedCount}</strong>
            behandlet
          </span>
          <span>
            <strong>{review.generation}</strong>
            generasjon
          </span>
        </div>
      </Card>
      ) : null}

      {view === "biltreff" ? (
      <Card className="work-card koble-qualified-card">
        <div className="koble-qualified-head">
          <div>
            <Typography.Text className="koble-review-eyebrow">Bilnummer med gjentatte treff</Typography.Text>
            <Typography.Title level={4}>
              {numberFormatter.format(Number(review.qualifiedPlateCount || 0))} bilnr har 2+ parkeringer med soltreff mot samme SUN2-bruker
            </Typography.Title>
            <Typography.Text type="secondary">
              Sortert etter flest ulike parkeringer med soltreff innen {review.maxMinutes} minutter etter parkering.
            </Typography.Text>
          </div>
          <div className="koble-qualified-summary-grid">
            <div className="koble-qualified-summary">
              <strong>{numberFormatter.format(Number(review.qualifiedPairCount || 0))}</strong>
              <span>kandidatkoblinger med 2+ parkeringer</span>
            </div>
            <div className="koble-qualified-summary">
              <strong>{formatKr(review.qualifiedMatchedPaidTotal)}</strong>
              <span>parkert ved soltreff</span>
            </div>
            <div className="koble-qualified-summary">
              <strong>{formatKr(review.qualifiedPaidTotal)}</strong>
              <span>parkert totalt</span>
            </div>
          </div>
        </div>

        {shownQualifiedRows.length ? (
          <div className="koble-qualified-list is-full">
            <div className="koble-qualified-row is-head">
              <span>Bil / SUN2</span>
              <span>Treff</span>
              <span>Siste treff</span>
              <span>Parkert ved soltreff</span>
              <span>Status</span>
              <span />
            </div>
            {shownQualifiedRows.map((row) => (
              <div className="koble-qualified-row" key={qualifiedRowKey(row)}>
                <div className="koble-qualified-identity">
                  <strong>{row.plate}</strong>
                  <span>
                    SUN2 {row.sun2Id}
                    {row.userName ? ` · ${row.userName}` : ""}
                  </span>
                  <small>{row.vehicleName || row.vehicleArea || "Kjøretøy mangler"}</small>
                </div>
                <div>
                  <strong>{row.matchesCount}</strong>
                  <span>{row.parkingMatchCount} parkeringer · {row.matchDaysCount} dager</span>
                </div>
                <div>
                  <strong>{formatDateTime(row.lastMatchAt)}</strong>
                  <span>{formatNumber(row.avgDeltaMinutes, " min snitt")}</span>
                </div>
                <div>
                  <strong>{formatKr(row.matchedPaidTotal)}</strong>
                  <span>{formatKr(row.paidTotal)} totalt</span>
                </div>
                <div>
                  <Tag color={statusColor(row.status)}>{row.status}</Tag>
                  <span>{Math.round(Number(row.confidence || 0))}%</span>
                </div>
                <div className="koble-qualified-actions">
                  {row.path ? <Button size="small" onClick={() => navigate(row.path || "/parkering/kjoretoy")}>Åpne bil</Button> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty description="Ingen bilnummer har to eller flere parkeringer med soltreff ennå" />
        )}

      </Card>
      ) : null}

      {view === "sun2" ? (
      <Card className="work-card koble-sun2-card">
        <div className="koble-sun2-head">
          <div>
            <Typography.Text className="koble-review-eyebrow">SUN2-basert kontroll</Typography.Text>
            <Typography.Title level={4}>Biler med 2+ parkeringer mot samme SUN2-ID</Typography.Title>
            <Typography.Text type="secondary">
              Viser {numberFormatter.format(qualifiedSun2Rows.length)} bil/SUN2-rader fordelt på {numberFormatter.format(qualifiedSun2Count)} SUN2-ID-er.
            </Typography.Text>
          </div>
          <Typography.Text type="secondary">
            Tabellen viser bare bil/SUN2-koblinger der minst to ulike parkeringer fikk soltime innen {review.maxMinutes} min.
          </Typography.Text>
        </div>

        {qualifiedSun2Rows.length ? (
          <div className="koble-sun2-table">
            <div className="koble-sun2-row is-head">
              <span>SUN2</span>
              <span>Bil</span>
              <span>Soltreff</span>
              <span>Parkeringer</span>
              <span>Uten soltreff</span>
              <span>Siste</span>
              <span>Status</span>
            </div>
            {qualifiedSun2Rows.map((row, index) => {
              const isNewSun2 = index === 0 || qualifiedSun2Rows[index - 1]?.sun2Id !== row.sun2Id;
              return (
                <div className={`koble-sun2-row${isNewSun2 ? " is-new-sun2" : ""}`} key={qualifiedSun2RowKey(row)}>
                  <div className="koble-sun2-id">
                    <strong>SUN2 {row.sun2Id}</strong>
                    <span>
                      {row.userName || "Ukjent bruker"}
                      {row.sun2VehicleCount > 1 ? ` · ${row.sun2VehicleCount} biler` : ""}
                    </span>
                  </div>
                  <div className="koble-sun2-car">
                    <strong>{row.plate}</strong>
                    <span>{row.vehicleName || row.vehicleArea || "Kjøretøy mangler"}</span>
                  </div>
                  <div>
                    <strong>{numberFormatter.format(Number(row.matchesCount || 0))}</strong>
                    <span>{row.matchDaysCount} dager · {formatNumber(row.avgDeltaMinutes, " min snitt")}</span>
                  </div>
                  <div>
                    <strong>{numberFormatter.format(Number(row.parkingMatchCount || 0))} av {numberFormatter.format(Number(row.parkingCount || 0))}</strong>
                    <span>{formatPercent(row.parkingMatchShare)} · {formatKr(row.matchedPaidTotal)} ved soltreff / {formatKr(row.paidTotal)} totalt</span>
                  </div>
                  <div>
                    <strong>{numberFormatter.format(Number(row.parkingWithoutSunCount || 0))}</strong>
                    <span>parkeringer uten soltreff</span>
                  </div>
                  <div>
                    <strong>{formatDateTime(row.lastMatchAt)}</strong>
                    <span>siste parkering med soltreff</span>
                  </div>
                  <div className="koble-sun2-status">
                    <Tag color={statusColor(row.status)}>{row.status}</Tag>
                    <span>{Math.round(Number(row.confidence || 0))}%</span>
                    {row.path ? <Button size="small" onClick={() => navigate(row.path || "/parkering/kjoretoy")}>Åpne</Button> : null}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <Empty description="Ingen SUN2-ID-er har biler med to eller flere parkeringer med soltreff ennå" />
        )}
      </Card>
      ) : null}

      {view === "kandidater" ? (
      visibleCandidates.length ? (
        <div className="koble-review-grid">
          {visibleCandidates.map((candidate) => {
            const tone = confidenceTone(candidate);
            const flags = candidateFlags(candidate);
            return (
              <Card className={`work-card koble-candidate-card is-${tone}`} key={candidate.id}>
                <div className="koble-candidate-head">
                  <div className="koble-candidate-title">
                    <Space size={6} wrap>
                      <Tag color={statusColor(candidate.status)}>{candidate.status}</Tag>
                      <Typography.Text type="secondary">{statusLabel(candidate)}</Typography.Text>
                    </Space>
                    <div className="koble-candidate-pair">
                      <strong>{candidate.plate}</strong>
                      <span>kobles mot</span>
                      <strong>SUN2 {candidate.sun2Id}</strong>
                    </div>
                  </div>
                  <div className="koble-confidence">
                    <strong>{Math.round(candidate.confidence)}%</strong>
                    <div className="koble-confidence-bar" aria-label={`Sannsynlighet ${Math.round(candidate.confidence)} prosent`}>
                      <span style={{ width: `${Math.max(0, Math.min(100, Math.round(candidate.confidence)))}%` }} />
                    </div>
                  </div>
                </div>

                <div className="koble-identity-grid">
                  <div>
                    <span>Bil/eier</span>
                    <strong>{candidate.vehicleName || "Ukjent"}</strong>
                    <small>{candidate.vehicleArea || "Område mangler"}</small>
                  </div>
                  <div>
                    <span>SUN2-bruker</span>
                    <strong>{candidate.userName || "Ukjent"}</strong>
                    <small>SUN2 {candidate.sun2Id}</small>
                  </div>
                  <div>
                    <span>Bilens historikk</span>
                    <strong>{candidate.parkingCount || 0} parkeringer</strong>
                    <small>{formatKr(candidate.matchedPaidTotal)} ved soltreff / {formatKr(candidate.paidTotal)} totalt</small>
                  </div>
                  <div>
                    <span>Tidsrom</span>
                    <strong>{formatDateTime(candidate.lastMatchAt)}</strong>
                    <small>første {formatDateTime(candidate.firstMatchAt)}</small>
                  </div>
                </div>

                <div className="koble-evidence-strip">
                  <div>
                    <strong>{candidate.parkingMatchCount}</strong>
                    <span>unike parkeringer</span>
                  </div>
                  <div>
                    <strong>{candidate.matchDaysCount}</strong>
                    <span>dager</span>
                  </div>
                  <div>
                    <strong>{formatNumber(candidate.avgDeltaMinutes, " min")}</strong>
                    <span>snitt etter parkering</span>
                  </div>
                  <div>
                    <strong>{candidate.matchesCount}</strong>
                    <span>soltreff</span>
                  </div>
                </div>

                <div className={`koble-flags ${flags.some((flag) => flag.includes("konkurrent") || flag.includes("alternativer")) ? "has-warning" : ""}`}>
                  {flags.map((flag) => (
                    <Tag key={flag}>{flag}</Tag>
                  ))}
                  {candidate.assessment ? <Typography.Text>{candidate.assessment}</Typography.Text> : null}
                </div>

                <div className="koble-match-list">
                  {candidate.matches.length ? (
                    candidate.matches.map((match) => (
                      <div className="koble-match-row" key={match.id}>
                        <div className="koble-match-time">
                          <strong>{formatDateTime(match.parkingStartAt)}</strong>
                          <span>Parkering {formatTime(match.parkingStartAt)}</span>
                        </div>
                        <div className="koble-match-delta">
                          <span>+{formatNumber(match.deltaMinutes, " min")}</span>
                        </div>
                        <div className="koble-match-session">
                          <strong>{formatTime(match.sunStartedAt)} soling</strong>
                          <span>
                            {match.roomLabel || "Rom ukjent"} · {formatNumber(match.durationMinutes, " min")} · {formatKr(match.paidAmountKr)}
                          </span>
                        </div>
                        <div className="koble-match-parking">
                          <strong>{formatKr(match.feeIncVat)}</strong>
                          <span>{match.sourceSystem || "Parkering"}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="koble-match-empty">Ingen detaljtreff i siste utsnitt. Rågrunnlaget ligger i tabellen under.</div>
                  )}
                </div>

                <div className="koble-candidate-actions">
                  <Space size={8} wrap>
                    <Button
                      type="primary"
                      loading={updatingId === candidate.id}
                      disabled={candidate.status === "Bekreftet"}
                      onClick={() => confirmCandidateStatus(candidate, "Bekreftet")}
                    >
                      Bekreft
                    </Button>
                    <Button
                      danger
                      loading={updatingId === candidate.id}
                      disabled={candidate.status === "Avvist"}
                      onClick={() => confirmCandidateStatus(candidate, "Avvist")}
                    >
                      Avvis
                    </Button>
                    <Tooltip title="Kopier SUN2-ID">
                      <Button onClick={() => copySun2(candidate)}>
                        Kopier SUN2
                      </Button>
                    </Tooltip>
                    {candidate.path ? (
                      <Button onClick={() => navigate(candidate.path || "/parkering/kjoretoy")}>
                        Åpne bil
                      </Button>
                    ) : null}
                  </Space>
                  {candidate.note ? <Typography.Text type="secondary">{candidate.note}</Typography.Text> : null}
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="work-card">
          <Empty description="Ingen kandidater å kontrollere" />
        </Card>
      )
      ) : null}

      {view === "kandidater" && shown < review.candidates.length ? (
        <div className="koble-review-more">
          <Button onClick={() => setShown((value) => Math.min(review.candidates.length, value + 10))}>
            Vis flere kandidater
          </Button>
        </div>
      ) : null}
    </section>
  );
}
