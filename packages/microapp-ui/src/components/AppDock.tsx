import { MosaicIcon, type IconName } from "./MosaicIcon";

export type AppDockId = "revenue" | "parking" | "sun" | "energy" | "operations" | "maintenance" | "system" | "link";

type AppDockItem = {
  id: AppDockId;
  name: string;
  icon: IconName;
  port: number;
  iconClass: string;
  activeClass: string;
};

const apps: AppDockItem[] = [
  { id: "revenue", name: "Omsetning", icon: "chart", port: 8151, iconClass: "text-red-500", activeClass: "bg-red-500/10 ring-red-500/20 dark:bg-red-500/20" },
  { id: "parking", name: "Parkering", icon: "parking", port: 8152, iconClass: "text-sky-500", activeClass: "bg-sky-500/10 ring-sky-500/20 dark:bg-sky-500/20" },
  { id: "sun", name: "Soling", icon: "sun", port: 8153, iconClass: "text-yellow-500", activeClass: "bg-yellow-500/10 ring-yellow-500/20 dark:bg-yellow-500/20" },
  { id: "link", name: "Koble", icon: "link", port: 8158, iconClass: "text-violet-500", activeClass: "bg-violet-500/10 ring-violet-500/20 dark:bg-violet-500/20" },
  { id: "energy", name: "Energi", icon: "energy", port: 8154, iconClass: "text-green-500", activeClass: "bg-green-500/10 ring-green-500/20 dark:bg-green-500/20" },
  { id: "operations", name: "Bygg og drift", icon: "building", port: 8155, iconClass: "text-violet-500", activeClass: "bg-violet-500/10 ring-violet-500/20 dark:bg-violet-500/20" },
  { id: "maintenance", name: "Vedlikehold", icon: "tools", port: 8156, iconClass: "text-green-600", activeClass: "bg-green-500/10 ring-green-500/20 dark:bg-green-500/20" },
  { id: "system", name: "System", icon: "settings", port: 8157, iconClass: "text-gray-500 dark:text-gray-300", activeClass: "bg-gray-200 ring-gray-300 dark:bg-gray-700 dark:ring-gray-600" },
];

function appUrl(shellUrl: string, port: number) {
  try {
    const url = new URL(shellUrl, window.location.href);
    url.port = String(port);
    url.pathname = "/";
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return `http://${window.location.hostname}:${port}/`;
  }
}

export function AppDock({ activeApp, shellUrl }: { activeApp?: AppDockId; shellUrl: string }) {
  return (
    <>
      <nav className="mr-2 hidden items-center gap-0.5 border-r border-gray-200 pr-4 dark:border-gray-700/60 md:flex" aria-label="Bytt app">
        {apps.map((app) => {
          const active = app.id === activeApp;
          return (
            <a
              className={`flex h-8 w-8 items-center justify-center rounded-full ring-1 ring-transparent transition-colors hover:bg-gray-200/80 dark:hover:bg-gray-800 ${active ? app.activeClass : ""}`}
              href={appUrl(shellUrl, app.port)}
              title={app.name}
              aria-label={`Åpne ${app.name}`}
              aria-current={active ? "page" : undefined}
              key={app.id}
            >
              <MosaicIcon name={app.icon} className={app.iconClass} />
            </a>
          );
        })}
      </nav>
      <a className="mr-2 flex h-8 w-8 items-center justify-center rounded-full text-violet-500 hover:bg-gray-200/80 dark:hover:bg-gray-800 md:hidden" href={shellUrl} title="Alle apper" aria-label="Åpne appvelger">
        <MosaicIcon name="apps" />
      </a>
    </>
  );
}
