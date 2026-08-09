import { MosaicIcon, type IconName } from "./MosaicIcon";
import { appDefinitions, resolveAppUrl } from "../navigation";
import type { AppDockId } from "../types";

export type { AppDockId } from "../types";

type AppDockItem = {
  id: AppDockId;
  name: string;
  icon: IconName;
  port: number;
  url: string;
  iconClass: string;
  activeClass: string;
};

const dockClasses: Record<AppDockId, Pick<AppDockItem, "iconClass" | "activeClass">> = {
  revenue: { iconClass: "text-red-500", activeClass: "bg-red-500/10 ring-red-500/20 dark:bg-red-500/20" },
  parking: { iconClass: "text-sky-500", activeClass: "bg-sky-500/10 ring-sky-500/20 dark:bg-sky-500/20" },
  sun: { iconClass: "text-yellow-500", activeClass: "bg-yellow-500/10 ring-yellow-500/20 dark:bg-yellow-500/20" },
  link: { iconClass: "text-violet-500", activeClass: "bg-violet-500/10 ring-violet-500/20 dark:bg-violet-500/20" },
  operations: { iconClass: "text-violet-500", activeClass: "bg-violet-500/10 ring-violet-500/20 dark:bg-violet-500/20" },
  energy: { iconClass: "text-green-500", activeClass: "bg-green-500/10 ring-green-500/20 dark:bg-green-500/20" },
  maintenance: { iconClass: "text-green-600", activeClass: "bg-green-500/10 ring-green-500/20 dark:bg-green-500/20" },
  system: { iconClass: "text-gray-500 dark:text-gray-300", activeClass: "bg-gray-200 ring-gray-300 dark:bg-gray-700 dark:ring-gray-600" },
};

const apps: AppDockItem[] = appDefinitions.map((app) => ({
  id: app.appId,
  name: app.shortName,
  icon: app.icon,
  port: app.port,
  url: app.url,
  ...dockClasses[app.appId],
}));

export function AppDock({ activeApp, shellUrl }: { activeApp?: AppDockId; shellUrl: string }) {
  return (
    <>
      <nav className="mr-2 hidden items-center gap-0.5 border-r border-gray-200 pr-4 dark:border-gray-700/60 md:flex" aria-label="Bytt app">
        <a className="mr-2 flex h-8 w-8 items-center justify-center rounded-full text-violet-500 transition-colors hover:bg-gray-200/80 dark:hover:bg-gray-800" href={shellUrl} title="Alle apper" aria-label="Åpne appvelger">
          <MosaicIcon name="apps" />
        </a>
        {apps.map((app) => {
          const active = app.id === activeApp;
          const separator = app.id === "operations" || app.id === "system";
          return (
            <a
              className={`flex h-8 w-8 items-center justify-center rounded-full ring-1 ring-transparent transition-colors hover:bg-gray-200/80 dark:hover:bg-gray-800 ${separator ? "ml-2" : ""} ${active ? app.activeClass : ""}`}
              href={resolveAppUrl(app)}
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
