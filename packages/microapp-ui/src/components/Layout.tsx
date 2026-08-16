import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { domainApi } from "../api";
import { useApi } from "../hooks";
import { findNavigationGroup, findNavigationItem } from "../navigation";
import { AppLink, useAppLocation } from "../router";
import type { Accent, DomainUiConfig, NavigationGroup, NavigationItem } from "../types";
import { AppDock } from "./AppDock";
import { MosaicIcon } from "./MosaicIcon";
import { ThemeToggle } from "./ThemeToggle";

const activeClasses: Record<Accent, string> = {
  violet: "bg-violet-500/[0.12] dark:bg-violet-500/[0.24]",
  sky: "bg-sky-500/[0.12] dark:bg-sky-500/[0.24]",
  yellow: "bg-yellow-500/[0.14] dark:bg-yellow-500/[0.22]",
  green: "bg-green-500/[0.12] dark:bg-green-500/[0.24]",
  red: "bg-red-500/[0.12] dark:bg-red-500/[0.24]",
};

const iconClasses: Record<Accent, string> = {
  violet: "text-violet-500",
  sky: "text-sky-500",
  yellow: "text-yellow-500",
  green: "text-green-500",
  red: "text-red-500",
};

const tabClasses: Record<Accent, string> = {
  violet: "border-violet-500 text-violet-600 dark:text-violet-400",
  sky: "border-sky-500 text-sky-600 dark:text-sky-400",
  yellow: "border-yellow-500 text-yellow-700 dark:text-yellow-400",
  green: "border-green-500 text-green-700 dark:text-green-400",
  red: "border-red-500 text-red-600 dark:text-red-400",
};

function Sidebar({ config, activeGroup, open, setOpen, coreUrl, build }: {
  config: DomainUiConfig;
  activeGroup: NavigationGroup;
  open: boolean;
  setOpen: (open: boolean) => void;
  coreUrl: string;
  build: string;
}) {
  const sidebar = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [expanded, setExpanded] = useState(() => window.localStorage.getItem("sidebar-expanded") === "true");

  useEffect(() => {
    window.localStorage.setItem("sidebar-expanded", String(expanded));
    document.body.classList.toggle("sidebar-expanded", expanded);
  }, [expanded]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      const target = event.target as Node;
      if (open && sidebar.current && trigger.current && !sidebar.current.contains(target) && !trigger.current.contains(target)) setOpen(false);
    };
    const closeWithKeyboard = (event: KeyboardEvent) => {
      if (open && event.key === "Escape") setOpen(false);
    };
    document.addEventListener("click", close);
    document.addEventListener("keydown", closeWithKeyboard);
    return () => {
      document.removeEventListener("click", close);
      document.removeEventListener("keydown", closeWithKeyboard);
    };
  }, [open, setOpen]);

  const labelClass = "ml-4 text-sm font-medium duration-200 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100";
  const activeClass = activeClasses[config.accent];
  const iconClass = iconClasses[config.accent];

  return (
    <div className="min-w-fit">
      <button type="button" tabIndex={-1} aria-label="Lukk meny" onClick={() => setOpen(false)} className={`fixed inset-0 z-40 bg-gray-900/30 transition-opacity duration-200 lg:hidden ${open ? "opacity-100" : "pointer-events-none opacity-0"}`} />
      <aside ref={sidebar} className={`absolute left-0 top-0 z-40 flex h-[100dvh] w-64 shrink-0 flex-col overflow-y-auto rounded-r-2xl bg-white p-4 shadow-xs transition-all duration-200 dark:bg-gray-800 lg:static lg:w-20 lg:translate-x-0 lg:sidebar-expanded:!w-64 2xl:w-64! ${open ? "translate-x-0" : "-translate-x-64"}`}>
        <div className="mb-8 flex justify-between pr-3 sm:px-2">
          <button ref={trigger} className="text-gray-500 lg:hidden" onClick={() => setOpen(false)}><span className="sr-only">Lukk meny</span><MosaicIcon name="arrow-left" size={22} /></button>
          <AppLink to="/" onClick={() => setOpen(false)} className="flex items-center text-xl font-bold text-gray-800 dark:text-gray-100">
            <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">{config.shortName}</span>
            <MosaicIcon name={config.icon} className={`${iconClass} lg:block lg:sidebar-expanded:hidden 2xl:hidden`} size={24} />
          </AppLink>
        </div>

        <nav aria-label={`${config.shortName} hovedomr\u00e5der`}>
          <ul className="space-y-1">
            {config.navigation.map((group) => {
              const active = group === activeGroup;
              return (
                <li className={`rounded-lg px-3 py-2 ${active ? activeClass : ""}`} key={group.label}>
                  <AppLink className="block truncate text-gray-800 dark:text-gray-100" to={group.items[0].to} onClick={() => setOpen(false)}>
                    <div className="flex items-center">
                      <MosaicIcon name={group.icon} className={active ? iconClass : "text-gray-400 dark:text-gray-500"} />
                      <span className={labelClass}>{group.label}</span>
                    </div>
                  </AppLink>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="mt-auto">
          <div className="px-3 py-2">
            <a className="flex items-center text-gray-800 dark:text-gray-100" href={coreUrl}><MosaicIcon name="external" className="text-gray-400 dark:text-gray-500" /><span className={labelClass}>Fibaro10</span></a>
          </div>
          <div className="hidden w-full justify-end pt-3 lg:inline-flex 2xl:hidden"><button className="w-12 px-4 py-2 text-gray-400" onClick={() => setExpanded(!expanded)} title="Utvid eller trekk sammen meny"><MosaicIcon name={expanded ? "arrow-left" : "arrow-right"} /></button></div>
          <div className="px-3 py-2 text-xs text-gray-400 lg:hidden lg:sidebar-expanded:block 2xl:block">Build {build}</div>
        </div>
      </aside>
    </div>
  );
}

function Header({ title, open, setOpen, username, activeApp, shellUrl }: {
  title: string;
  open: boolean;
  setOpen: (open: boolean) => void;
  username: string;
  activeApp: DomainUiConfig["appId"];
  shellUrl: string;
}) {
  return (
    <header className="sticky top-0 z-30 before:absolute before:inset-0 before:-z-10 before:bg-gray-100/90 before:backdrop-blur-md dark:before:bg-gray-900/90">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between border-b border-gray-200 dark:border-gray-700/60">
          <div className="flex min-w-0 items-center gap-3">
            <button className="shrink-0 text-gray-500 lg:hidden" aria-label="Åpne meny" aria-expanded={open} onClick={(event) => { event.stopPropagation(); setOpen(!open); }}><svg className="h-6 w-6 fill-current" viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="2" /><rect x="4" y="11" width="16" height="2" /><rect x="4" y="17" width="16" height="2" /></svg></button>
            <h1 className="truncate text-sm font-semibold text-gray-700 dark:text-gray-200">{title}</h1>
          </div>
          <div className="ml-4 flex shrink-0 items-center gap-3">
            <AppDock activeApp={activeApp} shellUrl={shellUrl} />
            <button className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-gray-800" title="Oppdater siden" aria-label="Oppdater siden" onClick={() => window.location.reload()}><MosaicIcon name="refresh" className="text-gray-500 dark:text-gray-400" /></button>
            <ThemeToggle />
            <hr className="h-6 w-px border-none bg-gray-200 dark:bg-gray-700" />
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-semibold uppercase text-gray-600 dark:bg-gray-700 dark:text-gray-200">{username.slice(0, 1)}</span>
            <span className="hidden text-sm font-medium text-gray-600 dark:text-gray-100 sm:block">{username}</span>
            <form method="post" action="/konto/logg-ut"><button className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-gray-800" title="Logg ut" aria-label="Logg ut"><MosaicIcon name="logout" className="text-gray-500 dark:text-gray-400" /></button></form>
          </div>
        </div>
      </div>
    </header>
  );
}

function ContextNavigation({ group, item, accent }: { group: NavigationGroup; item: NavigationItem; accent: Accent }) {
  if (group.items.length < 2) return null;
  return (
    <nav className="sticky top-16 z-20 border-b border-gray-200 bg-gray-100/95 backdrop-blur-md dark:border-gray-700/60 dark:bg-gray-900/95" aria-label={`${group.label} undersider`}>
      <div className="mx-auto flex h-12 max-w-[96rem] items-end gap-6 overflow-x-auto px-4 sm:px-6 lg:px-8">
        {group.items.map((candidate) => {
          const active = candidate === item;
          return <AppLink className={`flex h-12 shrink-0 items-center border-b-2 px-0.5 text-sm font-medium transition-colors ${active ? tabClasses[accent] : "border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100"}`} to={candidate.to} key={candidate.to}>{candidate.label}</AppLink>;
        })}
      </div>
    </nav>
  );
}

export function Layout({ config, children }: { config: DomainUiConfig; children: ReactNode }) {
  const location = useAppLocation();
  const appConfig = useApi(domainApi.config, "app-config");
  const user = useApi(domainApi.user, "current-user");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const item = useMemo(() => findNavigationItem(config, location.pathname), [config, location.pathname]);
  const group = useMemo(() => findNavigationGroup(config, item), [config, item]);
  const shellUrl = appConfig.data?.shellAppUrl || "https://app.lilletorget.net";

  useEffect(() => {
    document.title = `${item.title || item.label} · ${config.shortName}`;
  }, [config.shortName, item.label, item.title]);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <a href="#main-content" className="sr-only z-50 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 focus:not-sr-only focus:fixed focus:left-3 focus:top-3 dark:bg-gray-800 dark:text-white">Hopp til innhold</a>
      <Sidebar config={config} activeGroup={group} open={sidebarOpen} setOpen={setSidebarOpen} coreUrl={appConfig.data?.fibaro10AppUrl || "https://fibaro10.lilletorget.net"} build={appConfig.data?.build || "-"} />
      <div className="relative flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
        <Header title={item.title || item.label} open={sidebarOpen} setOpen={setSidebarOpen} username={user.data?.username || "Bruker"} activeApp={config.appId} shellUrl={shellUrl} />
        <ContextNavigation group={group} item={item} accent={config.accent} />
        <main id="main-content" tabIndex={-1} className="grow"><div className="mx-auto w-full max-w-[96rem] px-4 py-6 sm:px-6 lg:px-8">{children}</div></main>
      </div>
    </div>
  );
}
