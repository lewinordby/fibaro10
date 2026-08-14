import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AppDock } from "@lilletorget/microapp-ui/app-dock";
import { api } from "./api";
import { ThemeToggle } from "./ThemeToggle";
import type { AppConfig, AppRow, AppsResponse, AuthUser } from "./types";

type GlyphName = "apps" | "building" | "chart" | "energy" | "parking" | "settings" | "sun" | "tools";

const glyphPaths: Record<GlyphName, string[]> = {
  apps: ["M.06 10.003a1 1 0 0 1 1.948.455c-.019.08.01.152.078.19l5.83 3.333c.053.03.116.03.168 0l5.83-3.333a.163.163 0 0 0 .078-.188 1 1 0 0 1 1.947-.459 2.161 2.161 0 0 1-1.032 2.384l-5.83 3.331a2.168 2.168 0 0 1-2.154 0l-5.83-3.331a2.162 2.162 0 0 1-1.032-2.382Zm7.856-7.981-5.83 3.332a.17.17 0 0 0 0 .295l5.828 3.33c.054.031.118.031.17.002l5.83-3.333a.17.17 0 0 0 0-.294L8.085 2.023a.172.172 0 0 0-.17-.001ZM9.076.285l5.83 3.332c1.458.833 1.458 2.935 0 3.768l-5.83 3.333c-.667.38-1.485.38-2.153-.001l-5.83-3.332c-1.457-.833-1.457-2.935 0-3.767L6.925.285a2.173 2.173 0 0 1 2.15 0Z"],
  building: ["M1 15V3a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v3h2a2 2 0 0 1 2 2v7h-2V8h-2v7H1Zm3-10h2V3H4v2Zm0 4h2V7H4v2Zm0 4h2v-2H4v2Zm4-8h1V3H8v2Zm0 4h1V7H8v2Zm0 4h1v-2H8v2Z"],
  chart: ["M5.936.278A7.983 7.983 0 0 1 8 0a8 8 0 1 1-8 8c0-.722.104-1.413.278-2.064a1 1 0 1 1 1.932.516A5.99 5.99 0 0 0 2 8a6 6 0 1 0 6-6c-.53 0-1.045.076-1.548.21A1 1 0 1 1 5.936.278Z", "M6.068 7.482A2.003 2.003 0 0 0 8 10a2 2 0 1 0-.518-3.932L3.707 2.293a1 1 0 0 0-1.414 1.414l3.775 3.775Z"],
  energy: ["M9.6 0 2 9h5l-.6 7L14 7H9l.6-7Z"],
  parking: ["M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM6 4h2.75a2.75 2.75 0 1 1 0 5.5H8V12H6V4Zm2 2v1.5h.75a.75.75 0 0 0 0-1.5H8Z"],
  settings: ["M7.71 4.709a3 3 0 1 0 0 6 3 3 0 0 0 0-6ZM6.668.714a1 1 0 0 1-.673 1.244 6.014 6.014 0 0 0-4.037 4.037 1 1 0 1 1-1.916-.571A8.014 8.014 0 0 1 5.425.041a1 1 0 0 1 1.243.673ZM9.995.04a1 1 0 1 0-.57 1.918 6.014 6.014 0 0 1 4.036 4.037 1 1 0 0 0 1.917-.571A8.014 8.014 0 0 0 9.995.041ZM14.705 8.75a1 1 0 0 1 .673 1.244 8.014 8.014 0 0 1-5.383 5.384 1 1 0 0 1-.57-1.917 6.014 6.014 0 0 0 4.036-4.037 1 1 0 0 1 1.244-.673ZM1.958 9.424a1 1 0 0 0-1.916.57 8.014 8.014 0 0 0 5.383 5.384 1 1 0 0 0 .57-1.917 6.014 6.014 0 0 1-4.037-4.037Z"],
  sun: ["M8 0a1 1 0 0 1 1 1v.5a1 1 0 1 1-2 0V1a1 1 0 0 1 1-1ZM12 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm-4 2a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM13.657 3.757a1 1 0 0 0-1.414-1.414l-.354.354a1 1 0 0 0 1.414 1.414l.354-.354ZM13.5 8a1 1 0 0 1 1-1h.5a1 1 0 1 1 0 2h-.5a1 1 0 0 1-1-1ZM13.303 11.889a1 1 0 0 0-1.414 1.414l.354.354a1 1 0 0 0 1.414-1.414l-.354-.354ZM8 13.5a1 1 0 0 1 1 1v.5a1 1 0 1 1-2 0v-.5a1 1 0 0 1 1-1ZM4.111 13.303a1 1 0 1 0-1.414-1.414l-.354.354a1 1 0 1 0 1.414 1.414l.354-.354ZM0 8a1 1 0 0 1 1-1h.5a1 1 0 0 1 0 2H1a1 1 0 0 1-1-1ZM3.757 2.343a1 1 0 1 0-1.414 1.414l.354.354A1 1 0 1 0 4.11 2.697l-.354-.354Z"],
  tools: ["M14.7 2.7a4 4 0 0 1-5.1 5.1l-5.9 5.9a1 1 0 0 1-1.4-1.4l5.9-5.9a4 4 0 0 1 5.1-5.1l-2.1 2.1 1.4 1.4 2.1-2.1Z"],
};

function Glyph({ name, className = "text-gray-400 dark:text-gray-500", size = 16 }: { name: string; className?: string; size?: number }) {
  const paths = glyphPaths[(name in glyphPaths ? name : "apps") as GlyphName];
  return <svg className={`shrink-0 fill-current ${className}`} width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">{paths.map((path) => <path d={path} key={path} />)}</svg>;
}

function Spinner({ size = 20 }: { size?: number }) {
  return <svg className="animate-spin fill-current" width={size} height={size} viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0a8 8 0 1 1-7.446 5.06 1 1 0 0 1 1.86.735A6 6 0 1 0 8 2a1 1 0 0 1 0-2Z" /></svg>;
}

function Sidebar({ apps, config, open, setOpen }: { apps: AppRow[]; config: AppConfig | null; open: boolean; setOpen: (open: boolean) => void }) {
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
  return (
    <div className="min-w-fit">
      <div className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden lg:z-auto transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`} aria-hidden="true" />
      <div ref={sidebar} id="sidebar" className={`flex lg:flex! flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:!w-64 2xl:w-64! shrink-0 bg-white dark:bg-gray-800 p-4 transition-all duration-200 ease-in-out rounded-r-2xl shadow-xs ${open ? "translate-x-0" : "-translate-x-64"}`}>
        <div className="flex justify-between mb-10 pr-3 sm:px-2">
          <button ref={trigger} className="lg:hidden text-gray-500 hover:text-gray-400" onClick={() => setOpen(!open)} aria-controls="sidebar" aria-expanded={open}>
            <span className="sr-only">Lukk meny</span>
            <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="m10.7 18.7 1.4-1.4L7.8 13H20v-2H7.8l4.3-4.3-1.4-1.4L4 12z" /></svg>
          </button>
          <a href="/" className="flex items-center text-xl font-bold text-gray-800 dark:text-gray-100">
            <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Apper</span>
            <Glyph name="apps" className="text-violet-500 lg:block lg:sidebar-expanded:hidden 2xl:hidden" size={24} />
          </a>
        </div>

        <div className="space-y-8">
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Arbeidsflate</span>
            </h3>
            <ul className="mt-3">
              <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0 bg-violet-500/[0.12] dark:bg-violet-500/[0.24]">
                <a className="block text-gray-800 dark:text-gray-100 truncate transition duration-150" href="/">
                  <div className="flex items-center"><Glyph name="apps" className="text-violet-500" /><span className={labelClass}>Alle apper</span></div>
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">I drift</span>
            </h3>
            <ul className="mt-3">
              {apps.map((app) => (
                <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0" key={app.id}>
                  <a className="block text-gray-800 dark:text-gray-100 hover:text-gray-900 dark:hover:text-white truncate transition duration-150" href={app.url}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center min-w-0"><Glyph name={app.icon} /><span className={`${labelClass} truncate`}>{app.name}</span></div>
                      <span className={`hidden lg:sidebar-expanded:block 2xl:block w-2 h-2 rounded-full ${app.status === "ok" ? "bg-green-500" : "bg-red-500"}`} />
                    </div>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="pt-3 hidden lg:inline-flex 2xl:hidden justify-end mt-auto">
          <div className="w-12 pl-4 pr-3 py-2">
            <button className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400" onClick={() => setExpanded(!expanded)}>
              <span className="sr-only">Utvid eller trekk sammen meny</span>
              <svg className="shrink-0 fill-current sidebar-expanded:rotate-180" width="16" height="16" viewBox="0 0 16 16"><path d="M15 16a1 1 0 0 1-1-1V1a1 1 0 1 1 2 0v14a1 1 0 0 1-1 1ZM8.586 7H1a1 1 0 1 0 0 2h7.586l-2.793 2.793a1 1 0 1 0 1.414 1.414l4.5-4.5A.997.997 0 0 0 12 8.01M11.924 7.617a.997.997 0 0 0-.217-.324l-4.5-4.5a1 1 0 0 0-1.414 1.414L8.586 7M12 7.99a.996.996 0 0 0-.076-.373Z" /></svg>
            </button>
          </div>
        </div>
        <div className="mt-3 px-3 py-2 text-xs text-gray-400 dark:text-gray-500 lg:hidden lg:sidebar-expanded:block 2xl:block">Build {config?.build || "-"}</div>
      </div>
    </div>
  );
}

function Header({ open, setOpen, user, refreshing, refresh, shellUrl }: { open: boolean; setOpen: (open: boolean) => void; user: AuthUser | null; refreshing: boolean; refresh: () => void; shellUrl: string }) {
  return (
    <header className="sticky top-0 before:absolute before:inset-0 before:backdrop-blur-md max-lg:before:bg-white/90 dark:max-lg:before:bg-gray-800/90 before:-z-10 z-30 max-lg:shadow-xs lg:before:bg-gray-100/90 dark:lg:before:bg-gray-900/90">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:border-b border-gray-200 dark:border-gray-700/60">
          <div className="flex min-w-0 items-center">
            <button className="text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 lg:hidden" aria-controls="sidebar" aria-expanded={open} onClick={(event) => { event.stopPropagation(); setOpen(!open); }}>
              <span className="sr-only">Åpne meny</span>
              <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="2" /><rect x="4" y="11" width="16" height="2" /><rect x="4" y="17" width="16" height="2" /></svg>
            </button>
            <span className="ml-3 truncate text-sm font-semibold text-gray-700 dark:text-gray-200 lg:ml-0">Alle apper</span>
          </div>
          <div className="ml-4 flex shrink-0 items-center gap-3">
            <AppDock shellUrl={shellUrl} />
            <button className="w-8 h-8 flex items-center justify-center hover:bg-gray-100 lg:hover:bg-gray-200 dark:hover:bg-gray-700/50 dark:lg:hover:bg-gray-800 rounded-full" type="button" title="Oppdater status" onClick={refresh} disabled={refreshing}>
              {refreshing ? <Spinner size={16} /> : <svg className="fill-current text-gray-500/80 dark:text-gray-400/80" width="16" height="16" viewBox="0 0 16 16"><path d="M13.65 2.35A8 8 0 1 0 16 8h-2a6 6 0 1 1-1.76-4.24L9 7h7V0l-2.35 2.35Z" /></svg>}
            </button>
            <ThemeToggle />
            <hr className="w-px h-6 bg-gray-200 dark:bg-gray-700/60 border-none" />
            <div className="inline-flex justify-center items-center group">
              <span className="flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full w-8 h-8 text-xs font-semibold uppercase text-gray-500 dark:text-gray-300">{(user?.username || "?").slice(0, 1)}</span>
              <span className="hidden sm:block truncate ml-2 text-sm font-medium text-gray-600 dark:text-gray-100">{user?.username || "Bruker"}</span>
            </div>
            <form method="post" action="/konto/logg-ut">
              <button className="w-8 h-8 flex items-center justify-center hover:bg-gray-100 lg:hover:bg-gray-200 dark:hover:bg-gray-700/50 dark:lg:hover:bg-gray-800 rounded-full" title="Logg ut">
                <svg className="fill-current text-gray-500/80 dark:text-gray-400/80" width="16" height="16" viewBox="0 0 16 16"><path d="M7 14H2V2h5V0H1a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h6v-2Zm4.293-9.707L9.586 6H5v2h4.586l1.707 1.707 1.414-1.414L11.414 7l1.293-1.293-1.414-1.414ZM13 3l-1.414 1.414L13.172 6H13v2h.172l-1.586 1.586L13 11l3-3V6l-3-3Z" /></svg>
              </button>
            </form>
          </div>
        </div>
      </div>
    </header>
  );
}

const toneClasses: Record<string, { icon: string; badge: string }> = {
  revenue: { icon: "text-violet-500 bg-violet-500/10", badge: "text-violet-700 bg-violet-500/20" },
  parking: { icon: "text-sky-500 bg-sky-500/10", badge: "text-sky-700 bg-sky-500/20" },
  sun: { icon: "text-yellow-600 bg-yellow-500/10", badge: "text-yellow-800 bg-yellow-500/20" },
  energy: { icon: "text-green-600 bg-green-500/10", badge: "text-green-700 bg-green-500/20" },
  operations: { icon: "text-violet-500 bg-violet-500/10", badge: "text-violet-700 bg-violet-500/20" },
  maintenance: { icon: "text-violet-500 bg-violet-500/10", badge: "text-violet-700 bg-violet-500/20" },
  system: { icon: "text-gray-500 bg-gray-100 dark:bg-gray-700", badge: "text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300" },
};

function AppCard({ app }: { app: AppRow }) {
  const tone = toneClasses[app.tone] || toneClasses.system;
  const card = <>
    <div className="flex grow gap-4 px-5 py-5">
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${tone.icon}`}><Glyph name={app.icon} className="text-current" size={18} /></span>
      <div className="min-w-0">
        <div className="text-xs font-semibold uppercase text-gray-400 dark:text-gray-500">{app.category}</div>
        <h2 className="mt-0.5 text-lg font-semibold text-gray-800 dark:text-gray-100">{app.name}</h2>
        <p className="mt-1 text-sm leading-5 text-gray-500 dark:text-gray-400">{app.description}</p>
      </div>
    </div>
    <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3 dark:border-gray-700/60">
      <span className={`inline-flex items-center gap-2 text-xs font-medium ${app.status === "ok" ? "text-green-700 dark:text-green-400" : app.available ? "text-red-600 dark:text-red-400" : "text-gray-400"}`}><span className={`h-2 w-2 rounded-full ${app.status === "ok" ? "bg-green-500" : app.available ? "bg-red-500" : "bg-gray-400"}`} />{app.statusText}</span>
      <span className="text-xs font-medium text-violet-600 dark:text-violet-400">{app.available ? "Åpne →" : "Planlagt"}</span>
    </div>
  </>;
  const classes = "col-span-full flex min-h-44 flex-col rounded-lg bg-white shadow-sm transition-shadow sm:col-span-6 xl:col-span-3 dark:bg-gray-800";
  return app.available
    ? <a className={`${classes} hover:shadow-md`} href={app.url} title={app.build ? `${app.name}, build ${app.build}` : app.name}>{card}</a>
    : <div className={`${classes} opacity-75`}>{card}</div>;
}

export default function App() {
  const [appsData, setAppsData] = useState<AppsResponse | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (quiet = false) => {
    quiet ? setRefreshing(true) : setLoading(true);
    try {
      const [apps, currentUser, currentConfig] = await Promise.all([api.apps(), api.user(), api.config()]);
      setAppsData(apps); setUser(currentUser); setConfig(currentConfig); setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setLoading(false); setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(true), 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const activeApps = useMemo(() => appsData?.apps.filter((app) => app.available) ?? [], [appsData]);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar apps={activeApps} config={config} open={sidebarOpen} setOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header open={sidebarOpen} setOpen={setSidebarOpen} user={user} refreshing={refreshing} refresh={() => void load(true)} shellUrl={config?.shellUrl || "https://app.lilletorget.net"} />
        <main className="grow">
          <div className="px-4 py-6 sm:px-6 lg:px-8 w-full max-w-[96rem] mx-auto">
            {loading ? <div className="flex min-h-96 flex-col items-center justify-center gap-3 text-gray-400 dark:text-gray-500"><Spinner size={28} /><strong className="text-sm">Henter apper</strong></div> : null}
            {!loading && error ? <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-8 text-center"><svg className="mx-auto fill-current text-red-500" width="32" height="32" viewBox="0 0 16 16"><path d="M7.134 1.5a1 1 0 0 1 1.732 0l6.928 12A1 1 0 0 1 14.928 15H1.072a1 1 0 0 1-.866-1.5l6.928-12ZM7 6v4h2V6H7Zm0 5.5v2h2v-2H7Z" /></svg><h2 className="mt-3 font-semibold text-gray-800 dark:text-gray-100">Kunne ikke hente appstatus</h2><p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{error}</p><button className="btn mt-4 bg-gray-900 text-gray-100 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800" onClick={() => void load()}>Prøv igjen</button></div> : null}

            {!loading && !error && appsData ? (
              <>
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-4 dark:border-gray-700/60">
                  <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300"><span className={`h-2.5 w-2.5 rounded-full ${appsData.summary.healthy === appsData.summary.available ? "bg-green-500" : "bg-yellow-500"}`} /><strong className="text-gray-800 dark:text-gray-100">{appsData.summary.healthy} av {appsData.summary.available} apper klare</strong>{appsData.summary.planned ? <span>· {appsData.summary.planned} planlagt</span> : null}</div>
                  <span className="text-xs text-gray-400 dark:text-gray-500">Status oppdateres automatisk hvert 30. sekund</span>
                </div>
                <div className="grid grid-cols-12 gap-5">
                  {appsData.apps.map((app) => <AppCard app={app} key={app.id} />)}
                </div>
              </>
            ) : null}
          </div>
        </main>
      </div>
    </div>
  );
}
