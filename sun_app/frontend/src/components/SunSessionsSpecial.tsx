import { useEffect, useMemo, useState } from "react";
import { MosaicIcon, Panel, displayCell, nok, useAppSearchParams } from "@lilletorget/microapp-ui";
import type { ModuleRow, ModuleTable } from "@lilletorget/microapp-ui/types";
import { fetchSunSessionImages, selectSunSessionImage } from "../api";
import type { SunSessionImageBrowser, SunSessionSavedImage } from "../types";

function stringValue(row: ModuleRow, key: string) {
  const value = row[key];
  return value == null ? "" : String(value);
}

function numberValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function savedImages(row: ModuleRow) {
  return Array.isArray(row.session_images) ? row.session_images as SunSessionSavedImage[] : [];
}

function imageSource(path: string, version: string | number) {
  return `${path}${path.includes("?") ? "&" : "?"}v=${encodeURIComponent(version)}`;
}

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(value);
  const input = document.createElement("textarea");
  input.value = value;
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  input.remove();
}

function Field({ label, value }: { label: string; value: unknown }) {
  return <div className="min-w-0 border-b border-gray-100 py-2.5 last:border-0 dark:border-gray-700/60"><dt className="text-[11px] font-semibold uppercase text-gray-400">{label}</dt><dd className="mt-0.5 truncate text-sm font-medium text-gray-800 dark:text-gray-100">{value == null || value === "" ? "-" : String(value)}</dd></div>;
}

function Notice({ tone, children }: { tone: "error" | "success" | "info"; children: string }) {
  const classes = tone === "error" ? "bg-red-500/10 text-red-700 dark:text-red-300" : tone === "success" ? "bg-green-500/10 text-green-700 dark:text-green-300" : "bg-sky-500/10 text-sky-700 dark:text-sky-300";
  return <div className={`rounded-lg px-3 py-2 text-sm ${classes}`}>{children}</div>;
}

function ImageViewer({ row, reload }: { row: ModuleRow; reload: () => void }) {
  const sessionId = numberValue(row.id);
  const images = useMemo(() => savedImages(row), [row]);
  const defaultIndex = Math.max(0, images.findIndex((image) => image.isPrimary));
  const [savedIndex, setSavedIndex] = useState(defaultIndex);
  const [archive, setArchive] = useState<SunSessionImageBrowser | null>(null);
  const [large, setLarge] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ tone: "error" | "success" | "info"; text: string } | null>(null);

  useEffect(() => {
    setSavedIndex(defaultIndex);
    setArchive(null);
    setLarge(false);
    setNotice(null);
  }, [row.id, row.image_captured_at, row.image_count, defaultIndex]);

  const saved = images[savedIndex] || null;
  const snapshot = archive?.current || null;
  const imageUrl = snapshot ? imageSource(snapshot.imageUrl, snapshot.id) : saved ? imageSource(saved.imageUrl, saved.id) : "";
  const imageLabel = snapshot?.label || saved?.label || "";
  const snapshotId = snapshot?.id || saved?.snapshotId || "";
  const isPrimary = Boolean(snapshot?.isLinked || saved?.isPrimary);
  const canPrevious = snapshot ? Boolean(archive?.canPrevious) : Boolean(saved && (savedIndex > 0 || saved.snapshotId));
  const canNext = snapshot ? Boolean(archive?.canNext) : Boolean(saved && (savedIndex < images.length - 1 || saved.snapshotId));

  async function loadArchive(id?: string | null) {
    setBusy(true); setNotice(null);
    try { setArchive(await fetchSunSessionImages(sessionId, id)); }
    catch (reason) { setNotice({ tone: "error", text: reason instanceof Error ? reason.message : "Kunne ikke hente bildearkivet" }); }
    finally { setBusy(false); }
  }

  async function move(direction: -1 | 1) {
    if (busy) return;
    if (snapshot) {
      const next = direction < 0 ? archive?.previousSnapshotId : archive?.nextSnapshotId;
      if (next) await loadArchive(next);
      return;
    }
    const nextIndex = savedIndex + direction;
    if (nextIndex >= 0 && nextIndex < images.length) {
      setSavedIndex(nextIndex);
      setArchive(null);
      return;
    }
    if (!saved?.snapshotId) return;
    setBusy(true); setNotice(null);
    try {
      const edge = await fetchSunSessionImages(sessionId, saved.snapshotId);
      const next = direction < 0 ? edge.previousSnapshotId : edge.nextSnapshotId;
      if (!next) { setNotice({ tone: "info", text: direction < 0 ? "Ingen eldre bilder denne dagen." : "Ingen nyere bilder denne dagen." }); return; }
      setArchive(await fetchSunSessionImages(sessionId, next));
    } catch (reason) {
      setNotice({ tone: "error", text: reason instanceof Error ? reason.message : "Kunne ikke hente bildearkivet" });
    } finally { setBusy(false); }
  }

  async function selectCurrent() {
    if (!snapshotId || isPrimary || busy) return;
    setBusy(true); setNotice(null);
    try {
      const result = await selectSunSessionImage(sessionId, snapshotId);
      setArchive(result);
      setSavedIndex(Math.max(0, result.savedImages.findIndex((image) => image.isPrimary)));
      setNotice({ tone: "success", text: "Hovedbildet og de fem bildene rundt tidspunktet er lagret." });
      reload();
    } catch (reason) {
      setNotice({ tone: "error", text: reason instanceof Error ? reason.message : "Kunne ikke lagre bildepakken" });
    } finally { setBusy(false); }
  }

  if (!imageUrl) return <div className="flex min-h-72 flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-gray-300 bg-gray-50/60 p-6 text-center dark:border-gray-600 dark:bg-gray-900/20"><MosaicIcon name="sun" className="text-yellow-500" size={30} /><div><strong className="block text-gray-800 dark:text-gray-100">Ingen bilde er koblet til soltimen</strong><span className="mt-1 block text-sm text-gray-500 dark:text-gray-400">Åpne arkivet ved beregnet bildetid og velg riktig bilde.</span></div><button className="btn bg-yellow-500 text-gray-950 hover:bg-yellow-400" disabled={busy} onClick={() => loadArchive()}>{busy ? "Laster ..." : "Finn bilde i arkivet"}</button>{notice ? <Notice tone={notice.tone}>{notice.text}</Notice> : null}</div>;

  const viewer = <div className="relative overflow-hidden rounded-xl bg-gray-950"><img className="block max-h-[62vh] min-h-72 w-full object-contain" src={imageUrl} alt={`Axis-bilde ${imageLabel}`} loading="lazy" />{busy ? <div className="absolute inset-0 grid place-items-center bg-gray-950/45 text-sm font-medium text-white">Laster bilde ...</div> : null}<div className="absolute inset-x-0 bottom-0 flex flex-wrap items-end justify-between gap-3 bg-gradient-to-t from-black/80 via-black/35 to-transparent px-4 pb-4 pt-12 text-white"><div><strong className="block text-sm">{snapshot ? "Bildearkiv" : `${savedIndex + 1} av ${images.length} lagrede bilder`}</strong><span className="text-xs text-white/75">{saved?.offsetLabel ? `${saved.offsetLabel} · ` : ""}{imageLabel}</span></div><div className="flex items-center gap-2">{isPrimary ? <span className="rounded-full bg-yellow-400 px-2.5 py-1 text-xs font-semibold text-gray-950">Hovedbilde</span> : null}<button className="btn border-white/30 bg-black/25 text-white hover:bg-black/45" onClick={() => setLarge(true)}>Åpne stort</button></div></div></div>;

  return <div className="space-y-3">{viewer}<div className="grid grid-cols-[auto_auto_1fr_auto] gap-2"><button className="btn border-gray-200 bg-white text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200" aria-label="Forrige bilde" disabled={!canPrevious || busy} onClick={() => move(-1)}><MosaicIcon name="arrow-left" /></button><button className="btn border-gray-200 bg-white text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200" aria-label="Neste bilde" disabled={!canNext || busy} onClick={() => move(1)}><MosaicIcon name="arrow-right" /></button><div /><button className="btn bg-yellow-500 text-gray-950 hover:bg-yellow-400" disabled={!snapshotId || isPrimary || busy} onClick={selectCurrent}>{isPrimary ? "Valgt hovedbilde" : "Sett som hovedbilde"}</button></div>{notice ? <Notice tone={notice.tone}>{notice.text}</Notice> : null}{large ? <div className="fixed inset-0 z-50 grid place-items-center bg-gray-950/90 p-4" role="dialog" aria-modal="true" onClick={() => setLarge(false)}><div className="relative max-h-full max-w-7xl" onClick={(event) => event.stopPropagation()}><img className="max-h-[90vh] max-w-full object-contain" src={imageUrl} alt={`Axis-bilde ${imageLabel}`} /><button className="absolute right-3 top-3 rounded-full bg-black/70 px-4 py-2 text-sm font-semibold text-white" onClick={() => setLarge(false)}>Lukk</button></div></div> : null}</div>;
}

function SessionDetails({ row, reload }: { row: ModuleRow; reload: () => void }) {
  const [copyNotice, setCopyNotice] = useState("");
  const sun2Id = stringValue(row, "sun2_user_id");
  const copy = async () => {
    if (!sun2Id) return;
    try { await copyText(sun2Id); setCopyNotice("Kopiert"); window.setTimeout(() => setCopyNotice(""), 1800); }
    catch { setCopyNotice("Kunne ikke kopiere"); }
  };
  return <div className="grid gap-5 border-t border-gray-100 bg-gray-50/50 p-5 lg:grid-cols-[minmax(15rem,0.72fr)_minmax(28rem,2fr)] dark:border-gray-700/60 dark:bg-gray-900/15"><div className="min-w-0"><div className="mb-3 rounded-lg border border-yellow-300/70 bg-yellow-50 px-3 py-3 dark:border-yellow-500/30 dark:bg-yellow-500/10"><span className="text-[11px] font-semibold uppercase text-yellow-700 dark:text-yellow-300">SUN2-ID / medlemsnummer</span><div className="mt-1 flex items-center justify-between gap-3"><strong className="truncate text-base text-gray-900 dark:text-white">{sun2Id || "-"}</strong><button className="btn border-yellow-300 bg-white text-yellow-800 dark:border-yellow-500/40 dark:bg-gray-800 dark:text-yellow-300" disabled={!sun2Id} onClick={copy}>{copyNotice || "Kopier"}</button></div></div><dl><Field label="Start" value={displayCell("started_at", row.started_at)} /><Field label="Slutt" value={displayCell("ended_at", row.ended_at)} /><Field label="Rom" value={row.room_label || row.room || row.room_id} /><Field label="Varighet" value={row.duration_minutes ? `${nok(numberValue(row.duration_minutes))} min` : "-"} /><Field label="Betalt" value={row.paid_amount_kr != null ? `${nok(numberValue(row.paid_amount_kr))} kr` : "-"} /><Field label="Bruker" value={row.user_name} /><Field label="Betaling" value={row.payment_method} /><Field label="Kundetype" value={row.customer_type} /><Field label="Status" value={row.status} /></dl></div><ImageViewer row={row} reload={reload} /></div>;
}

function SessionRow({ row, reload }: { row: ModuleRow; reload: () => void }) {
  const [open, setOpen] = useState(false);
  const imageCount = numberValue(row.image_count);
  return <article className={`overflow-hidden border-b border-gray-100 last:border-0 dark:border-gray-700/60 ${open ? "bg-white dark:bg-gray-800" : ""}`}><button className="grid w-full grid-cols-[minmax(9.5rem,1.15fr)_minmax(6.5rem,0.65fr)_minmax(8rem,1fr)_auto] items-center gap-4 px-5 py-3.5 text-left transition hover:bg-gray-50 dark:hover:bg-gray-700/25" aria-expanded={open} onClick={() => setOpen((value) => !value)}><div className="min-w-0"><strong className="block truncate text-sm text-gray-900 dark:text-gray-100">{displayCell("started_at", row.started_at)}</strong><span className="mt-0.5 block truncate text-xs text-gray-500 dark:text-gray-400">{stringValue(row, "user_name") || stringValue(row, "sun2_user_id") || "Ukjent bruker"}</span></div><div><strong className="block text-sm text-gray-800 dark:text-gray-100">{String(row.room_label || row.room || row.room_id || "-")}</strong><span className="text-xs text-gray-500">{row.duration_minutes ? `${nok(numberValue(row.duration_minutes))} min` : "Tid -"}</span></div><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">{row.paid_amount_kr != null ? `${nok(numberValue(row.paid_amount_kr))} kr` : "Beløp -"}</span><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${imageCount ? "bg-green-500/10 text-green-700 dark:text-green-300" : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"}`}>{imageCount ? `${imageCount} bilder` : "Ingen bilder"}</span></div><MosaicIcon name={open ? "chevron-up" : "chevron-down"} className="text-gray-400" /></button>{open ? <SessionDetails row={row} reload={reload} /> : null}</article>;
}

export function SunSessionsSpecial({ table, reload }: { table?: ModuleTable; reload: () => void }) {
  const [, setParams] = useAppSearchParams();
  const rows = table?.rows || [];
  const meta = table?.meta;
  const changePage = (page: number) => { const next = new URLSearchParams(window.location.search); next.set("page", String(Math.max(1, page))); setParams(next); };
  return <Panel title="Enkeltimer" subtitle={meta?.totalRows != null ? `${meta.totalRows.toLocaleString("nb-NO")} soltimer i valgt utvalg · Trykk på en soltime for detaljer og bilder` : "Trykk på en soltime for detaljer og bilder"}><div>{rows.map((row, index) => <SessionRow key={String(row.id || index)} row={row} reload={reload} />)}{!rows.length ? <div className="px-5 py-12 text-center text-sm text-gray-500 dark:text-gray-400">Ingen soltimer i valgt utvalg.</div> : null}</div>{meta && !meta.disablePagination && (meta.hasPrevious || meta.hasMore) ? <footer className="flex items-center justify-between border-t border-gray-100 px-5 py-3 dark:border-gray-700/60"><span className="text-xs text-gray-500">{meta.firstRow || 0}-{meta.lastRow || rows.length} av {meta.totalRows || rows.length}</span><div className="flex gap-2"><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!meta.hasPrevious} onClick={() => changePage((meta.page || 1) - 1)}>Forrige</button><button className="btn border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800" disabled={!meta.hasMore} onClick={() => changePage((meta.page || 1) + 1)}>Neste</button></div></footer> : null}</Panel>;
}
