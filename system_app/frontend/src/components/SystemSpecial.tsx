import { useMemo, useState } from "react";
import { MetricCard, MosaicIcon, Panel } from "@lilletorget/microapp-ui";
import type { SystemNotificationsData, SystemSubsystem, SystemSubsystemsData } from "../types";

const accessLabels = { external: "Ekstern", local: "Internt nett", internal: "Intern tjeneste" } as const;

function StatusPill({ active, label }: { active: boolean; label: string }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${active ? "bg-green-500/10 text-green-700 dark:text-green-300" : "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300"}`}><span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-green-500" : "bg-yellow-500"}`} />{label}</span>;
}

export function NotificationsSpecial({ data }: { data: SystemNotificationsData }) {
  return <div className="space-y-5">
    <div className="grid gap-4 sm:grid-cols-3">
      <MetricCard label="Kanaler" value={data.summary.channels} unit="stk" detail="Tilgjengelige abonnement" tone="violet" />
      <MetricCard label="Konfigurert" value={data.summary.configured} unit="stk" detail="Har privat kanaladresse" tone="green" />
      <MetricCard label="Publiserer" value={data.summary.publishing} unit="stk" detail="Sender automatiske varsler" tone="sky" />
    </div>
    <div className="grid gap-5 xl:grid-cols-2">
      {data.subscriptions.map((channel) => <Panel key={channel.key} title={channel.title} subtitle={channel.area} actions={<StatusPill active={channel.configured && channel.publishingEnabled} label={!channel.configured ? "Ikke konfigurert" : channel.publishingEnabled ? "Aktiv" : "Utsending avslått"} />}>
        <div className="space-y-4 p-5">
          <p className="text-sm leading-6 text-gray-500 dark:text-gray-400">{channel.description}</p>
          <div className="flex flex-wrap gap-2">{channel.triggers.map((trigger) => <span className="rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700/70 dark:text-gray-300" key={trigger}>{trigger}</span>)}</div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4 dark:border-gray-700/70">
            <span className="text-xs font-medium text-gray-400">Prioritet: {channel.priority}</span>
            <div className="flex gap-2">
              {channel.subscribeUrl ? <a className="btn bg-violet-500 text-white hover:bg-violet-600" href={channel.subscribeUrl}><MosaicIcon name="bell" />Abonner</a> : null}
              {channel.webUrl ? <a className="btn border-gray-200 bg-white text-gray-600 hover:text-gray-900 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" href={channel.webUrl} target="_blank" rel="noreferrer"><MosaicIcon name="external" />Åpne kanal</a> : null}
            </div>
          </div>
        </div>
      </Panel>)}
    </div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(18rem,0.65fr)]">
      <Panel title="Slik kobler du til" subtitle="Første gangs oppsett"><ol className="space-y-3 p-5">{data.setup.map((step, index) => <li className="grid grid-cols-[1.75rem_1fr] gap-3 text-sm text-gray-600 dark:text-gray-300" key={step}><span className="flex h-7 w-7 items-center justify-center rounded-full bg-violet-500/10 font-semibold text-violet-600 dark:text-violet-300">{index + 1}</span><span className="pt-1">{step}</span></li>)}</ol></Panel>
      <Panel title="Personvern" subtitle={data.provider}><div className="flex gap-3 p-5 text-sm leading-6 text-gray-500 dark:text-gray-400"><MosaicIcon name="warning" className="mt-1 text-yellow-500" /><p>{data.privacy}</p></div></Panel>
    </div>
  </div>;
}

function accessTone(access: SystemSubsystem["access"]) {
  return access === "external" ? "bg-sky-500/10 text-sky-700 dark:text-sky-300" : access === "local" ? "bg-green-500/10 text-green-700 dark:text-green-300" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
}

export function SubsystemsSpecial({ data }: { data: SystemSubsystemsData }) {
  const [access, setAccess] = useState<"all" | SystemSubsystem["access"]>("all");
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("nb-NO");
    const filtered = data.subsystems.filter((row) => (access === "all" || (row.access || "internal") === access) && (!needle || [row.title, row.component, row.area, row.role, row.compose_service].join(" ").toLocaleLowerCase("nb-NO").includes(needle)));
    const mapped = new Map<string, SystemSubsystem[]>();
    filtered.forEach((row) => mapped.set(row.area || "Annet", [...(mapped.get(row.area || "Annet") || []), row]));
    return [...mapped.entries()].sort(([left], [right]) => left.localeCompare(right, "nb")).map(([areaName, rows]) => ({ areaName, rows: rows.sort((left, right) => left.title.localeCompare(right.title, "nb")) }));
  }, [access, data.subsystems, query]);
  return <div className="space-y-5">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Komponenter" value={data.summary.components} unit="stk" detail="Apper og tjenester" tone="violet" /><MetricCard label="Aktive" value={data.summary.active} unit="stk" detail="I daglig drift" tone="green" /><MetricCard label="Kritiske" value={data.summary.critical} unit="stk" detail="Påvirker datagrunnlaget" tone="red" /><MetricCard label="Webflater" value={data.summary.web_interfaces} unit="stk" detail="Kan åpnes direkte" tone="sky" /></div>
    <Panel><div className="flex flex-wrap items-center justify-between gap-3 p-4"><div className="flex flex-wrap gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-700/70">{([['all','Alle'],['external','Eksterne'],['local','Internt nett'],['internal','Interne tjenester']] as const).map(([key, label]) => <button className={`rounded-md px-3 py-1.5 text-sm ${access === key ? "bg-white font-semibold text-gray-800 shadow-sm dark:bg-gray-800 dark:text-gray-100" : "text-gray-500"}`} onClick={() => setAccess(key)} key={key}>{label}</button>)}</div><label className="relative"><span className="sr-only">Søk etter app eller tjeneste</span><input className="form-input w-72 max-w-full" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Søk etter app eller tjeneste" /></label></div></Panel>
    {groups.map((group) => <section className="space-y-3" key={group.areaName}><header className="flex items-center gap-2 px-1"><h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100">{group.areaName}</h2><span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-700">{group.rows.length}</span></header><div className="grid gap-4 xl:grid-cols-2">{group.rows.map((row) => { const rowAccess = row.access || "internal"; const links = row.links || []; return <Panel key={row.component}><div className="space-y-4 p-5"><div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold text-gray-800 dark:text-gray-100">{row.primary_url ? <a href={row.primary_url} target="_blank" rel="noreferrer" className="hover:text-violet-500">{row.title || row.component}</a> : row.title || row.component}</h3><p className="mt-1 text-sm leading-5 text-gray-500 dark:text-gray-400">{row.role}</p></div><span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${accessTone(rowAccess)}`}>{accessLabels[rowAccess]}</span></div><div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-400"><span>{row.runtime}</span>{row.compose_service ? <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-700">{row.compose_service}</code> : null}<span>{row.criticality}</span><span>{row.status}</span></div>{links.length ? <div className="flex flex-wrap gap-2 border-t border-gray-100 pt-4 dark:border-gray-700/70">{links.map((link) => <a className={`btn ${link.kind === "public" ? "bg-violet-500 text-white hover:bg-violet-600" : "border-gray-200 bg-white text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"}`} href={link.url} target="_blank" rel="noreferrer" key={`${link.kind}-${link.url}`}><MosaicIcon name={link.kind === "health" ? "refresh" : "external"} />{link.label}</a>)}</div> : null}</div></Panel>; })}</div></section>)}
    {!groups.length ? <Panel><div className="p-10 text-center text-sm text-gray-400">Ingen undersystemer passer med filteret.</div></Panel> : null}
  </div>;
}
