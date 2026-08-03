import { type ReactNode, useEffect, useRef, useState } from "react";
import { MosaicIcon, ThemeToggle } from "@lilletorget/microapp-ui/primitives";
import { useApi } from "@lilletorget/microapp-ui/hooks";
import { AppLink, useAppLocation } from "@lilletorget/microapp-ui/router";
import { api } from "../api";

const navigation = [
  { to: "/", label: "Dashboard", icon: "dashboard" as const },
  { to: "/oversikt", label: "Oversikt", icon: "chart" as const },
  { to: "/sammenligning", label: "Periodesammenligning", icon: "compare" as const },
  { to: "/ar", label: "Årssammenligning", icon: "trend" as const },
  { to: "/maned", label: "Månedsoversikt", icon: "calendar" as const },
];

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/oversikt": "Omsetningsoversikt",
  "/sammenligning": "Periodesammenligning",
  "/ar": "Årssammenligning",
  "/maned": "Månedsoversikt",
};

function Sidebar({ open, setOpen, shellUrl, fibaroUrl, build }: { open: boolean; setOpen: (open: boolean) => void; shellUrl: string; fibaroUrl: string; build: string }) {
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
  return (
    <div className="min-w-fit">
      <div className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden lg:z-auto transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`} aria-hidden="true" />
      <div ref={sidebar} id="sidebar" className={`flex lg:flex! flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:!w-64 2xl:w-64! shrink-0 bg-white dark:bg-gray-800 p-4 transition-all duration-200 ease-in-out rounded-r-2xl shadow-xs ${open ? "translate-x-0" : "-translate-x-64"}`}>
        <div className="flex justify-between mb-10 pr-3 sm:px-2">
          <button ref={trigger} className="lg:hidden text-gray-500 hover:text-gray-400" onClick={() => setOpen(!open)} aria-controls="sidebar" aria-expanded={open}>
            <span className="sr-only">Lukk meny</span>
            <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="m10.7 18.7 1.4-1.4L7.8 13H20v-2H7.8l4.3-4.3-1.4-1.4L4 12z" /></svg>
          </button>
          <AppLink to="/" className="flex items-center text-xl font-bold text-gray-800 dark:text-gray-100">
            <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Omsetning</span>
            <MosaicIcon name="chart" className="text-violet-500 lg:block lg:sidebar-expanded:hidden 2xl:hidden" size={24} />
          </AppLink>
        </div>

        <div className="space-y-8">
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Apper</span>
            </h3>
            <ul className="mt-3">
              <li className="px-3 py-2 rounded-lg mb-0.5 last:mb-0">
                <a className="block text-gray-800 dark:text-gray-100 hover:text-gray-900 dark:hover:text-white truncate transition duration-150" href={shellUrl}>
                  <div className="flex items-center"><MosaicIcon name="apps" className="text-gray-400 dark:text-gray-500" /><span className={labelClass}>Alle apper</span></div>
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Omsetning</span>
            </h3>
            <ul className="mt-3">
              {navigation.map((item) => {
                const active = location.pathname === item.to;
                return (
                  <li className={`px-3 py-2 rounded-lg mb-0.5 last:mb-0 ${active ? "bg-violet-500/[0.12] dark:bg-violet-500/[0.24]" : ""}`} key={item.to}>
                    <AppLink className={`block truncate transition duration-150 ${active ? "text-gray-800 dark:text-gray-100" : "text-gray-800 dark:text-gray-100 hover:text-gray-900 dark:hover:text-white"}`} to={item.to}>
                      <div className="flex items-center"><MosaicIcon name={item.icon} className={active ? "text-violet-500" : "text-gray-400 dark:text-gray-500"} /><span className={labelClass}>{item.label}</span></div>
                    </AppLink>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>

        <div className="mt-auto">
          <div className="px-3 py-2">
            <a className="flex items-center text-gray-800 dark:text-gray-100 hover:text-gray-900 dark:hover:text-white transition duration-150" href={fibaroUrl}>
              <MosaicIcon name="external" className="text-gray-400 dark:text-gray-500" /><span className={labelClass}>Fibaro10</span>
            </a>
          </div>
          <div className="pt-3 hidden lg:inline-flex 2xl:hidden justify-end w-full">
            <div className="w-12 pl-4 pr-3 py-2"><button className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400" onClick={() => setExpanded(!expanded)}><span className="sr-only">Utvid eller trekk sammen meny</span><svg className="shrink-0 fill-current sidebar-expanded:rotate-180" width="16" height="16" viewBox="0 0 16 16"><path d="M15 16a1 1 0 0 1-1-1V1a1 1 0 1 1 2 0v14a1 1 0 0 1-1 1ZM8.586 7H1a1 1 0 1 0 0 2h7.586l-2.793 2.793a1 1 0 1 0 1.414 1.414l4.5-4.5A.997.997 0 0 0 12 8.01M11.924 7.617a.997.997 0 0 0-.217-.324l-4.5-4.5a1 1 0 0 0-1.414 1.414L8.586 7M12 7.99a.996.996 0 0 0-.076-.373Z" /></svg></button></div>
          </div>
          <div className="px-3 py-2 text-xs text-gray-400 dark:text-gray-500 lg:hidden lg:sidebar-expanded:block 2xl:block">Build {build}</div>
        </div>
      </div>
    </div>
  );
}

function Header({ open, setOpen, username, title }: { open: boolean; setOpen: (open: boolean) => void; username: string; title: string }) {
  return (
    <header className="sticky top-0 before:absolute before:inset-0 before:backdrop-blur-md max-lg:before:bg-white/90 dark:max-lg:before:bg-gray-800/90 before:-z-10 z-30 max-lg:shadow-xs lg:before:bg-gray-100/90 dark:lg:before:bg-gray-900/90">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:border-b border-gray-200 dark:border-gray-700/60">
          <div className="flex items-center">
            <button className="text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 lg:hidden" aria-controls="sidebar" aria-expanded={open} onClick={(event) => { event.stopPropagation(); setOpen(!open); }}>
              <span className="sr-only">Åpne meny</span><svg className="w-6 h-6 fill-current" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="2" /><rect x="4" y="11" width="16" height="2" /><rect x="4" y="17" width="16" height="2" /></svg>
            </button>
            <span className="ml-3 text-sm font-semibold text-gray-700 dark:text-gray-200 lg:ml-0">{title}</span>
          </div>
          <div className="flex items-center space-x-3">
            <button className="w-8 h-8 flex items-center justify-center hover:bg-gray-100 lg:hover:bg-gray-200 dark:hover:bg-gray-700/50 dark:lg:hover:bg-gray-800 rounded-full" type="button" title="Oppdater siden" onClick={() => window.location.reload()}><MosaicIcon name="refresh" className="text-gray-500/80 dark:text-gray-400/80" /></button>
            <ThemeToggle />
            <hr className="w-px h-6 bg-gray-200 dark:bg-gray-700/60 border-none" />
            <div className="inline-flex justify-center items-center group">
              <span className="flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full w-8 h-8 text-xs font-semibold uppercase text-gray-500 dark:text-gray-300">{username.slice(0, 1)}</span>
              <span className="hidden sm:block truncate ml-2 text-sm font-medium text-gray-600 dark:text-gray-100">{username}</span>
            </div>
            <form method="post" action="/konto/logg-ut"><button className="w-8 h-8 flex items-center justify-center hover:bg-gray-100 lg:hover:bg-gray-200 dark:hover:bg-gray-700/50 dark:lg:hover:bg-gray-800 rounded-full" title="Logg ut"><MosaicIcon name="logout" className="text-gray-500/80 dark:text-gray-400/80" /></button></form>
          </div>
        </div>
      </div>
    </header>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const location = useAppLocation();
  const { data: config } = useApi(api.config, "app-config");
  const { data: user } = useApi(api.user, "current-user");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const title = titles[location.pathname] ?? titles["/"];

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} shellUrl={config?.shellAppUrl || "http://192.168.20.218:8150"} fibaroUrl={config?.fibaro10AppUrl || "http://192.168.20.218:8110"} build={config?.build || "-"} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header open={sidebarOpen} setOpen={setSidebarOpen} username={user?.username || "Bruker"} title={title} />
        <main className="grow">
          <div className="px-4 py-6 sm:px-6 lg:px-8 w-full max-w-[96rem] mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
