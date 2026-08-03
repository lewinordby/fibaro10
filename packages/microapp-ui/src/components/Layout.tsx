import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { domainApi } from "../api";
import { useApi } from "../hooks";
import { AppLink, useAppLocation } from "../router";
import type { Accent, DomainUiConfig, NavigationItem } from "../types";
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

function Sidebar({ config, open, setOpen, shellUrl, coreUrl, build }: { config: DomainUiConfig; open: boolean; setOpen: (open: boolean) => void; shellUrl: string; coreUrl: string; build: string }) {
  const location = useAppLocation();
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
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [open, setOpen]);

  const labelClass = "text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200";
  const activeClass = activeClasses[config.accent];
  const iconClass = iconClasses[config.accent];
  return (
    <div className="min-w-fit">
      <div className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`} aria-hidden="true" />
      <div ref={sidebar} className={`flex flex-col absolute z-40 left-0 top-0 lg:static lg:translate-x-0 h-[100dvh] overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:!w-64 2xl:w-64! shrink-0 bg-white dark:bg-gray-800 p-4 transition-all duration-200 rounded-r-2xl shadow-xs ${open ? "translate-x-0" : "-translate-x-64"}`}>
        <div className="flex justify-between mb-8 pr-3 sm:px-2">
          <button ref={trigger} className="lg:hidden text-gray-500" onClick={() => setOpen(false)}><span className="sr-only">Lukk meny</span><MosaicIcon name="arrow-left" size={22} /></button>
          <AppLink to="/" className="flex items-center text-xl font-bold text-gray-800 dark:text-gray-100"><span className="lg:hidden lg:sidebar-expanded:block 2xl:block">{config.shortName}</span><MosaicIcon name={config.icon} className={`${iconClass} lg:block lg:sidebar-expanded:hidden 2xl:hidden`} size={24} /></AppLink>
        </div>
        <nav className="space-y-7">
          <div>
            <div className="px-3 py-2"><a className="flex items-center text-gray-800 dark:text-gray-100" href={shellUrl}><MosaicIcon name="apps" className="text-gray-400 dark:text-gray-500" /><span className={labelClass}>Alle apper</span></a></div>
          </div>
          {config.navigation.map((group) => (
            <div key={group.label}>
              <h3 className="pl-3 text-xs font-semibold uppercase text-gray-400 dark:text-gray-500"><span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6">•••</span><span className="lg:hidden lg:sidebar-expanded:block 2xl:block">{group.label}</span></h3>
              <ul className="mt-2">
                {group.items.map((item) => {
                  const active = location.pathname === item.to || (item.to !== "/" && location.pathname.startsWith(`${item.to}/`));
                  return <li className={`px-3 py-2 rounded-lg mb-0.5 ${active ? activeClass : ""}`} key={item.to}><AppLink className="block truncate text-gray-800 dark:text-gray-100" to={item.to}><div className="flex items-center"><MosaicIcon name={item.icon} className={active ? iconClass : "text-gray-400 dark:text-gray-500"} /><span className={labelClass}>{item.label}</span></div></AppLink></li>;
                })}
              </ul>
            </div>
          ))}
        </nav>
        <div className="mt-auto">
          <div className="px-3 py-2"><a className="flex items-center text-gray-800 dark:text-gray-100" href={coreUrl}><MosaicIcon name="external" className="text-gray-400 dark:text-gray-500" /><span className={labelClass}>Fibaro10</span></a></div>
          <div className="pt-3 hidden lg:inline-flex 2xl:hidden justify-end w-full"><button className="w-12 px-4 py-2 text-gray-400" onClick={() => setExpanded(!expanded)} title="Utvid eller trekk sammen meny"><MosaicIcon name={expanded ? "arrow-left" : "arrow-right"} /></button></div>
          <div className="px-3 py-2 text-xs text-gray-400 lg:hidden lg:sidebar-expanded:block 2xl:block">Build {build}</div>
        </div>
      </div>
    </div>
  );
}

function Header({ title, open, setOpen, username, activeApp, shellUrl }: { title: string; open: boolean; setOpen: (open: boolean) => void; username: string; activeApp: DomainUiConfig["appId"]; shellUrl: string }) {
  return <header className="sticky top-0 before:absolute before:inset-0 before:backdrop-blur-md before:-z-10 z-30 before:bg-gray-100/90 dark:before:bg-gray-900/90"><div className="px-4 sm:px-6 lg:px-8"><div className="flex h-16 items-center justify-between border-b border-gray-200 dark:border-gray-700/60"><div className="flex min-w-0 items-center gap-3"><button className="shrink-0 text-gray-500 lg:hidden" aria-expanded={open} onClick={(event) => { event.stopPropagation(); setOpen(!open); }}><span className="sr-only">Åpne meny</span><svg className="h-6 w-6 fill-current" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="2" /><rect x="4" y="11" width="16" height="2" /><rect x="4" y="17" width="16" height="2" /></svg></button><span className="truncate text-sm font-semibold text-gray-700 dark:text-gray-200">{title}</span></div><div className="ml-4 flex shrink-0 items-center gap-3"><AppDock activeApp={activeApp} shellUrl={shellUrl} /><button className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-gray-800" title="Oppdater siden" onClick={() => window.location.reload()}><MosaicIcon name="refresh" className="text-gray-500 dark:text-gray-400" /></button><ThemeToggle /><hr className="h-6 w-px border-none bg-gray-200 dark:bg-gray-700" /><span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-semibold uppercase text-gray-600 dark:bg-gray-700 dark:text-gray-200">{username.slice(0, 1)}</span><span className="hidden text-sm font-medium text-gray-600 dark:text-gray-100 sm:block">{username}</span><form method="post" action="/konto/logg-ut"><button className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-200 dark:hover:bg-gray-800" title="Logg ut"><MosaicIcon name="logout" className="text-gray-500 dark:text-gray-400" /></button></form></div></div></div></header>;
}

export function Layout({ config, children }: { config: DomainUiConfig; children: ReactNode }) {
  const location = useAppLocation();
  const appConfig = useApi(domainApi.config, "app-config");
  const user = useApi(domainApi.user, "current-user");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const item = useMemo<NavigationItem>(() => {
    const items = config.navigation.flatMap((group) => group.items);
    return items.find((entry) => entry.to === location.pathname)
      || items.filter((entry) => entry.to !== "/" && location.pathname.startsWith(`${entry.to}/`)).sort((a, b) => b.to.length - a.to.length)[0]
      || items[0];
  }, [config, location.pathname]);
  const shellUrl = appConfig.data?.shellAppUrl || "http://192.168.20.218:8150";
  return <div className="flex h-[100dvh] overflow-hidden"><Sidebar config={config} open={sidebarOpen} setOpen={setSidebarOpen} shellUrl={shellUrl} coreUrl={appConfig.data?.fibaro10AppUrl || "http://192.168.20.218:8110"} build={appConfig.data?.build || "-"} /><div className="relative flex flex-1 flex-col overflow-x-hidden overflow-y-auto"><Header title={item.label} open={sidebarOpen} setOpen={setSidebarOpen} username={user.data?.username || "Bruker"} activeApp={config.appId} shellUrl={shellUrl} /><main className="grow"><div className="mx-auto w-full max-w-[96rem] px-4 py-6 sm:px-6 lg:px-8">{children}</div></main></div></div>;
}
