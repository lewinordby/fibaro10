import { useLocation } from "react-router-dom";
import { AppRoutes } from "./AppRoutes";
import { AppShell } from "./components/AppShell";
import { defaultModuleView, MODULE_VIEWS } from "./moduleViews";

function activeModule(pathname: string): string | null {
  const module = pathname.split("/")[1];
  return MODULE_VIEWS[module] ? module : null;
}

export default function App() {
  const location = useLocation();
  const module = activeModule(location.pathname);
  const viewItems = module ? MODULE_VIEWS[module] ?? [] : [];
  const rawActiveView = module ? location.pathname.split("/")[2] || defaultModuleView(module) : "";
  const activeView = module && viewItems.some((item) => item.key === rawActiveView) ? rawActiveView : defaultModuleView(module || "");

  return (
    <AppShell activeView={activeView} module={module} viewItems={viewItems}>
      <AppRoutes />
    </AppShell>
  );
}
