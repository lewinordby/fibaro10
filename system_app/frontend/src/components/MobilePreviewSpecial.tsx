import { Panel } from "@lilletorget/microapp-ui";
import type { ModuleTable } from "@lilletorget/microapp-ui/types";

export function MobilePreviewSpecial({ table }: { table?: ModuleTable }) {
  const rows = table?.rows || [];
  return <div className="grid gap-5 xl:grid-cols-2 2xl:grid-cols-3">{rows.map((row, index) => {
    const title = String(row.skjerm || `Mobilflate ${index + 1}`);
    const src = String(row["forhåndsvisning"] || row.forhandsvisning || "");
    return <Panel title={title} subtitle={String(row.forklaring || row.kilde || "")} key={`${title}-${index}`}><div className="flex min-h-[42rem] justify-center overflow-hidden bg-gray-100 p-4 dark:bg-gray-950/40">{src ? <iframe className="h-[46rem] w-full max-w-[28rem] rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700" src={src} title={title} loading="lazy" /> : <div className="p-8 text-sm text-gray-500">Forhåndsvisning mangler.</div>}</div></Panel>;
  })}</div>;
}
