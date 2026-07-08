import { useLocation } from "react-router-dom";
import { AppRoutes } from "./AppRoutes";
import { AppShell } from "./components/AppShell";
import { defaultModuleView, MODULE_VIEWS, visibleModuleViews } from "./moduleViews";

function activeModule(pathname: string): string | null {
  const module = pathname.split("/")[1];
  return MODULE_VIEWS[module] ? module : null;
}

export default function App() {
  const location = useLocation();
  const module = activeModule(location.pathname);
  const allViewItems = module ? MODULE_VIEWS[module] ?? [] : [];
  const visibleViewItems = module ? visibleModuleViews(module) : [];
  const rawActiveView = module ? location.pathname.split("/")[2] || defaultModuleView(module) : "";
  const activeItem = allViewItems.find((item) => item.key === rawActiveView);
  const viewItems = activeItem?.hidden ? [...visibleViewItems, activeItem] : visibleViewItems;
  const activeView = module && activeItem ? rawActiveView : defaultModuleView(module || "");

  return (
    <AppShell activeView={activeView} module={module} viewItems={viewItems}>
      <AppRoutes />
    </AppShell>
  );
}
