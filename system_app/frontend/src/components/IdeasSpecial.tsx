import { Panel } from "@lilletorget/microapp-ui";
import type { ModuleRow } from "@lilletorget/microapp-ui/types";

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : value ? [String(value)] : [];
}

function tone(area: string) {
  if (area === "Omsetning") return "border-l-red-500";
  if (area === "Parkering") return "border-l-sky-500";
  if (area === "Soling") return "border-l-yellow-400";
  if (area === "Energi") return "border-l-green-500";
  if (area === "Koble") return "border-l-violet-500";
  return "border-l-gray-400";
}

function statusTone(status: string) {
  if (status === "Klar å bygge") return "bg-green-500/15 text-green-700 dark:text-green-300";
  if (status === "Eksperiment") return "bg-violet-500/15 text-violet-700 dark:text-violet-300";
  if (status === "Krever datagrunnlag") return "bg-yellow-500/15 text-yellow-700 dark:text-yellow-300";
  return "bg-sky-500/15 text-sky-700 dark:text-sky-300";
}

export function IdeasSpecial({ rows }: { rows: ModuleRow[] }) {
  const impactRank: Record<string, number> = { Høy: 0, Middels: 1, Lav: 2 };
  const statusRank: Record<string, number> = { "Klar å bygge": 0, "Bør vurderes": 1, Eksperiment: 2, "Krever datagrunnlag": 3 };
  const prioritized = [...rows].sort((left, right) => (impactRank[String(left.nytte)] ?? 9) - (impactRank[String(right.nytte)] ?? 9) || (statusRank[String(left.status)] ?? 9) - (statusRank[String(right.status)] ?? 9)).slice(0, 3);
  return <div className="space-y-5"><Panel title="Forslag til neste grep" subtitle="Prioritert etter nytte og hvor klart forslaget er å bygge"><ol className="grid gap-3 p-5 lg:grid-cols-3">{prioritized.map((idea, index) => <li className="grid grid-cols-[2rem_1fr] gap-3 rounded-lg bg-gray-50 p-4 dark:bg-gray-700/30" key={String(idea.id)}><span className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-500/15 text-sm font-semibold text-violet-700 dark:text-violet-300">{index + 1}</span><div><strong className="block text-sm text-gray-800 dark:text-gray-100">{String(idea.forslag)}</strong><span className="mt-1 block text-xs text-gray-400">{String(idea.mål)}</span></div></li>)}</ol></Panel><section className="grid gap-5 xl:grid-cols-2">{rows.map((idea) => { const area = String(idea.område || "System"); const status = String(idea.status || ""); return <article className={`rounded-lg border border-gray-200 border-l-4 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800 ${tone(area)}`} key={String(idea.id || idea.forslag)}><header className="flex flex-wrap items-start justify-between gap-3"><div><span className="text-xs font-semibold uppercase text-gray-400">{area}</span><h3 className="mt-1 text-lg font-semibold text-gray-800 dark:text-gray-100">{String(idea.forslag)}</h3></div><div className="flex flex-wrap gap-2"><span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">{String(idea.nytte)} nytte</span><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusTone(status)}`}>{status}</span></div></header><p className="mt-3 text-sm leading-6 text-gray-600 dark:text-gray-300">{String(idea.oppsummering || "")}</p><div className="mt-4 rounded-lg bg-gray-50 px-4 py-3 dark:bg-gray-700/30"><span className="text-[11px] font-semibold uppercase text-gray-400">Flyttes trolig til</span><strong className="mt-0.5 block text-sm text-gray-800 dark:text-gray-100">{String(idea.mål || "-")}</strong></div><div className="mt-5 grid gap-5 lg:grid-cols-3"><div><h4 className="text-xs font-semibold uppercase text-gray-400">Hvorfor</h4><p className="mt-2 text-sm leading-5 text-gray-600 dark:text-gray-300">{String(idea.hvorfor || "-")}</p></div><div><h4 className="text-xs font-semibold uppercase text-gray-400">Må bygges</h4><ul className="mt-2 space-y-2 text-sm text-gray-600 dark:text-gray-300">{strings(idea.må_bygges).map((item) => <li className="flex gap-2" key={item}><span className="text-green-500">•</span><span>{item}</span></li>)}</ul></div><div><h4 className="text-xs font-semibold uppercase text-gray-400">Kontrollpunkter</h4><ul className="mt-2 space-y-2 text-sm text-gray-600 dark:text-gray-300">{strings(idea.kontrollpunkter).map((item) => <li className="flex gap-2" key={item}><span className="text-violet-500">•</span><span>{item}</span></li>)}</ul></div></div></article>; })}</section></div>;
}
