import { useMemo, useState } from "react";
import { domainApi } from "../api";
import { nok } from "../format";
import type { KobleQualifiedRow, KobleQualifiedSun2Row, KobleReviewCandidate, KobleReviewData } from "../types";
import { Panel } from "./Mosaic";
import { MosaicIcon } from "./MosaicIcon";

function dateTime(value?: string | null) {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "-" : parsed.toLocaleString("nb-NO", { dateStyle: "short", timeStyle: "short" });
}

function time(value?: string | null) {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "-" : parsed.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" });
}

function money(value?: number | null) {
  return `${nok(Number(value || 0), 0)} kr`;
}

function parkingHref(path?: string | null) {
  if (!path) return "";
  const parsed = new URL(path, window.location.origin);
  const localPath = parsed.pathname.replace(/^\/parkering/, "") || "/";
  return `https://parkering.lilletorget.net:8443${localPath}${parsed.search}`;
}

function Status({ value }: { value: string }) {
  const tone = value === "Bekreftet" ? "bg-green-500/15 text-green-600 dark:text-green-400" : value === "Avvist" ? "bg-red-500/15 text-red-600 dark:text-red-400" : "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400";
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${tone}`}>{value}</span>;
}

function QualifiedCars({ review }: { review: KobleReviewData }) {
  const rows = review.qualifiedRows || [];
  return <Panel title="Biler med gjentatte treff" subtitle={`Minst ${review.minMatches} ulike parkeringer mot samme Sun2-ID innen ${review.maxMinutes} minutter`}>
    <div className="grid gap-3 border-b border-gray-100 p-5 dark:border-gray-700 sm:grid-cols-3">
      <div><span className="text-xs uppercase text-gray-400">Bilnummer</span><strong className="block text-xl text-gray-800 dark:text-gray-100">{review.qualifiedPlateCount || 0}</strong></div>
      <div><span className="text-xs uppercase text-gray-400">Bil/Sun2-par</span><strong className="block text-xl text-gray-800 dark:text-gray-100">{review.qualifiedPairCount || 0}</strong></div>
      <div><span className="text-xs uppercase text-gray-400">Parkert ved soltreff</span><strong className="block text-xl text-gray-800 dark:text-gray-100">{money(review.qualifiedMatchedPaidTotal)}</strong></div>
    </div>
    <QualifiedTable rows={rows} />
  </Panel>;
}

function QualifiedTable({ rows }: { rows: KobleQualifiedRow[] }) {
  return <div className="overflow-x-auto"><table className="table-auto w-full"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/50"><tr><th className="px-4 py-3 text-left">Bil / Sun2</th><th className="px-4 py-3 text-left">Treff</th><th className="px-4 py-3 text-left">Parkeringer</th><th className="px-4 py-3 text-left">Siste</th><th className="px-4 py-3 text-left">Omsetning</th><th className="px-4 py-3 text-left">Status</th></tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{rows.map((row) => <tr key={`${row.id}-${row.plate}-${row.sun2Id}`}><td className="px-4 py-3"><strong className="block text-gray-800 dark:text-gray-100">{row.plate} · Sun2 {row.sun2Id}</strong><span className="text-xs text-gray-400">{row.vehicleName || row.vehicleArea || row.userName || "Ukjent"}</span></td><td className="px-4 py-3 tabular-nums"><strong>{row.matchesCount}</strong><span className="block text-xs text-gray-400">{row.matchDaysCount} dager · {nok(row.avgDeltaMinutes || 0, 1)} min</span></td><td className="px-4 py-3 tabular-nums">{row.parkingMatchCount} av {row.parkingCount || 0}</td><td className="px-4 py-3 whitespace-nowrap">{dateTime(row.lastMatchAt)}</td><td className="px-4 py-3 tabular-nums"><strong>{money(row.matchedPaidTotal)}</strong><span className="block text-xs text-gray-400">{money(row.paidTotal)} totalt</span></td><td className="px-4 py-3"><div className="flex items-center gap-3"><Status value={row.status} />{row.path ? <a className="font-medium text-violet-600 hover:underline dark:text-violet-400" href={parkingHref(row.path)}>Bil</a> : null}</div></td></tr>)}{!rows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={6}>Ingen kvalifiserte biler ennå</td></tr> : null}</tbody></table></div>;
}

function Sun2Control({ review }: { review: KobleReviewData }) {
  const rows = review.qualifiedSun2Rows || [];
  const sun2Count = new Set(rows.map((row) => row.sun2Id)).size;
  return <Panel title="Sun2-kontroll" subtitle={`${rows.length} bilkoblinger fordelt på ${sun2Count} Sun2-ID-er`}><div className="overflow-x-auto"><table className="table-auto w-full"><thead className="bg-gray-50 text-xs uppercase text-gray-400 dark:bg-gray-700/50"><tr><th className="px-4 py-3 text-left">Sun2</th><th className="px-4 py-3 text-left">Bil</th><th className="px-4 py-3 text-left">Soltreff</th><th className="px-4 py-3 text-left">Parkeringer</th><th className="px-4 py-3 text-left">Uten sol</th><th className="px-4 py-3 text-left">Siste</th><th className="px-4 py-3 text-left">Status</th></tr></thead><tbody className="divide-y divide-gray-100 text-sm dark:divide-gray-700/60">{rows.map((row: KobleQualifiedSun2Row) => <tr key={`${row.id}-${row.plate}-${row.sun2Id}`}><td className="px-4 py-3"><strong>Sun2 {row.sun2Id}</strong><span className="block text-xs text-gray-400">{row.userName || "Ukjent bruker"} · {row.sun2VehicleCount} biler</span></td><td className="px-4 py-3"><strong>{row.plate}</strong><span className="block text-xs text-gray-400">{row.vehicleName || row.vehicleArea || "Ukjent"}</span></td><td className="px-4 py-3 tabular-nums">{row.matchesCount}<span className="block text-xs text-gray-400">{row.matchDaysCount} dager</span></td><td className="px-4 py-3 tabular-nums">{row.parkingMatchCount} av {row.parkingCount || 0}<span className="block text-xs text-gray-400">{nok(row.parkingMatchShare || 0, 1)} %</span></td><td className="px-4 py-3 tabular-nums">{row.parkingWithoutSunCount}</td><td className="px-4 py-3 whitespace-nowrap">{dateTime(row.lastMatchAt)}</td><td className="px-4 py-3"><Status value={row.status} /></td></tr>)}{!rows.length ? <tr><td className="px-5 py-10 text-center text-gray-400" colSpan={7}>Ingen Sun2-ID-er oppfyller kravet ennå</td></tr> : null}</tbody></table></div></Panel>;
}

function CandidateCard({ candidate, minMatches, busy, update }: { candidate: KobleReviewCandidate; minMatches: number; busy: boolean; update: (candidate: KobleReviewCandidate, status: "Bekreftet" | "Avvist") => void }) {
  const confidence = Math.max(0, Math.min(100, Math.round(candidate.confidence || 0)));
  return <Panel><div className="border-l-4 border-violet-500 p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="flex items-center gap-2"><Status value={candidate.status} /><span className="text-xs text-gray-400">{candidate.parkingMatchCount >= minMatches ? "Kvalifisert" : `Krever ${minMatches} parkeringer`}</span></div><h3 className="mt-2 text-xl font-semibold text-gray-800 dark:text-gray-100">{candidate.plate} <span className="text-sm font-normal text-gray-400">mot</span> Sun2 {candidate.sun2Id}</h3><p className="text-sm text-gray-500">{candidate.vehicleName || candidate.vehicleArea || "Ukjent bil/eier"} · {candidate.userName || "Ukjent Sun2-bruker"}</p></div><div className="min-w-32 text-right"><strong className="text-2xl text-gray-800 dark:text-gray-100">{confidence} %</strong><div className="mt-1 h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700"><span className="block h-full bg-violet-500" style={{ width: `${confidence}%` }} /></div></div></div><div className="mt-4 grid gap-3 rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-700/35 sm:grid-cols-4"><span><small className="block text-gray-400">Parkeringer</small><strong>{candidate.parkingMatchCount}</strong></span><span><small className="block text-gray-400">Soltreff</small><strong>{candidate.matchesCount}</strong></span><span><small className="block text-gray-400">Dager</small><strong>{candidate.matchDaysCount}</strong></span><span><small className="block text-gray-400">Snitt etter ankomst</small><strong>{nok(candidate.avgDeltaMinutes || 0, 1)} min</strong></span></div><div className="mt-4 divide-y divide-gray-100 rounded-lg border border-gray-100 dark:divide-gray-700 dark:border-gray-700">{candidate.matches.map((match) => <div className="grid grid-cols-[1fr_auto_1fr_auto] items-center gap-3 px-3 py-2 text-xs" key={match.id}><span>{dateTime(match.parkingStartAt)}</span><strong className="text-violet-600">+{nok(match.deltaMinutes || 0, 1)} min</strong><span>{time(match.sunStartedAt)} · {match.roomLabel || "Rom"} · {nok(match.durationMinutes || 0, 0)} min</span><span className="tabular-nums">{money(match.feeIncVat)}</span></div>)}</div>{candidate.assessment ? <p className="mt-3 text-sm text-gray-500">{candidate.assessment}</p> : null}<div className="mt-4 flex flex-wrap items-center gap-2"><button className="btn bg-green-600 text-white hover:bg-green-700" disabled={busy || candidate.status === "Bekreftet"} onClick={() => update(candidate, "Bekreftet")}>Bekreft</button><button className="btn border-red-200 bg-white text-red-600 hover:bg-red-50 dark:border-red-900 dark:bg-gray-800" disabled={busy || candidate.status === "Avvist"} onClick={() => update(candidate, "Avvist")}>Avvis</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => navigator.clipboard.writeText(candidate.sun2Id)}><MosaicIcon name="copy" />Kopier Sun2-ID</button>{candidate.path ? <a className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" href={parkingHref(candidate.path)}>Åpne bil</a> : null}</div></div></Panel>;
}

function Candidates({ review, reload }: { review: KobleReviewData; reload: () => void }) {
  const [shown, setShown] = useState(10);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const rows = useMemo(() => review.candidates.slice(0, shown), [review.candidates, shown]);
  const update = async (candidate: KobleReviewCandidate, status: "Bekreftet" | "Avvist") => {
    if (!window.confirm(`${status} kobling mellom ${candidate.plate} og Sun2 ${candidate.sun2Id}?`)) return;
    setBusyId(candidate.id); setMessage("");
    try { await domainApi.mutate(`/api/koble/candidates/${candidate.id}`, "PATCH", { status }); setMessage("Koblingen er oppdatert"); reload(); }
    catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { setBusyId(null); }
  };
  return <div className="space-y-5">{message ? <div className="rounded-lg bg-violet-500/10 px-4 py-3 text-sm text-violet-700 dark:text-violet-300">{message}</div> : null}<div className="grid gap-5 xl:grid-cols-2">{rows.map((candidate) => <CandidateCard candidate={candidate} minMatches={review.minMatches} busy={busyId === candidate.id} update={update} key={candidate.id} />)}</div>{!rows.length ? <Panel><div className="p-10 text-center text-gray-400">Ingen kvalifiserte kandidater</div></Panel> : null}{shown < review.candidates.length ? <button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" onClick={() => setShown((value) => value + 10)}>Vis flere</button> : null}</div>;
}

export function LinkReviewSpecial({ review, view, reload }: { review: KobleReviewData; view: string; reload: () => void }) {
  if (view === "biltreff") return <QualifiedCars review={review} />;
  if (view === "sun2" || view === "sun2-kontroll") return <Sun2Control review={review} />;
  if (view === "kandidater") return <Candidates review={review} reload={reload} />;
  if (view !== "oversikt") return null;
  return <Panel title="Slik kvalifiseres en kobling" subtitle={`Samme bil og samme Sun2-ID på minst ${review.minMatches} ulike parkeringer, med solstart innen ${review.maxMinutes} minutter`}><div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-4"><div><span className="text-xs uppercase text-gray-400">Kandidater</span><strong className="block text-2xl text-gray-800 dark:text-gray-100">{review.candidateCount}</strong></div><div><span className="text-xs uppercase text-gray-400">Sterke</span><strong className="block text-2xl text-gray-800 dark:text-gray-100">{review.strongCandidateCount}</strong></div><div><span className="text-xs uppercase text-gray-400">Enkelttreff, ikke kandidater</span><strong className="block text-2xl text-gray-800 dark:text-gray-100">{review.rawOneOffPairCount || 0}</strong></div><div><span className="text-xs uppercase text-gray-400">Parkeringer behandlet</span><strong className="block text-2xl text-gray-800 dark:text-gray-100">{review.processedCount}</strong></div></div></Panel>;
}
