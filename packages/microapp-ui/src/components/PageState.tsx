import { MosaicIcon } from "./MosaicIcon";

export function Loading() {
  return <div className="flex min-h-96 flex-col items-center justify-center gap-3 text-gray-500 dark:text-gray-400" role="status" aria-live="polite"><MosaicIcon name="refresh" className="animate-spin" size={28} /><strong className="text-sm">Henter data</strong></div>;
}

export function ErrorState({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  return (
    <div className="rounded-xl bg-white p-8 text-center shadow-sm dark:bg-gray-800" role="alert">
      <MosaicIcon name="warning" className="mx-auto text-red-500" size={32} />
      <strong className="mt-3 block text-base text-gray-800 dark:text-gray-100">Kunne ikke hente data</strong>
      <span className="mx-auto mt-1 block max-w-xl text-sm text-gray-500 dark:text-gray-400">{error?.message || "Ukjent feil"}</span>
      <button className="btn mt-4 bg-gray-900 text-gray-100 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800 dark:hover:bg-white" onClick={onRetry}><MosaicIcon name="refresh" />Prøv igjen</button>
    </div>
  );
}
