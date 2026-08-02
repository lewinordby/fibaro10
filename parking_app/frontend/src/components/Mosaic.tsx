import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Panel({ title, subtitle, actions, children, className = "" }: { title?: string; subtitle?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`bg-white dark:bg-gray-800 shadow-sm rounded-xl ${className}`}>
      {title || subtitle || actions ? (
        <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center justify-between gap-6">
          <div>{title ? <h2 className="font-semibold text-gray-800 dark:text-gray-100">{title}</h2> : null}{subtitle ? <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{subtitle}</p> : null}</div>
          {actions}
        </header>
      ) : null}
      {children}
    </section>
  );
}

export function MetricCard({ label, value, unit, detail, tone = "gray" }: { label: string; value: string | number; unit?: string; detail?: string; tone?: "violet" | "red" | "sky" | "yellow" | "green" | "gray" }) {
  const toneClass = { violet: "text-violet-500", red: "text-red-500", sky: "text-sky-500", yellow: "text-yellow-500", green: "text-green-500", gray: "text-gray-400 dark:text-gray-500" }[tone];
  return (
    <article className="min-w-0 bg-white dark:bg-gray-800 shadow-sm rounded-xl px-5 py-5">
      <div className={`text-xs font-semibold uppercase mb-1 ${toneClass}`}>{label}</div>
      <div className="flex items-start"><div className="text-3xl font-bold text-gray-800 dark:text-gray-100 tabular-nums">{value}</div>{unit ? <span className="ml-2 mt-1 text-sm font-medium text-gray-400 dark:text-gray-500">{unit}</span> : null}</div>
      {detail ? <p className="mt-2 truncate text-xs text-gray-500 dark:text-gray-400">{detail}</p> : null}
    </article>
  );
}

export function Segmented({ options, value, onChange }: { options: Array<{ value: string; label: string }>; value: string; onChange: (value: string) => void }) {
  return (
    <div className="flex flex-wrap -m-1">
      {options.map((option) => (
        <button className={`m-1 inline-flex items-center justify-center rounded-full border px-3 py-1 text-sm leading-5 font-medium shadow-sm transition ${value === option.value ? "border-transparent bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-800" : "border-gray-200 bg-white text-gray-500 hover:border-gray-300 dark:border-gray-700/60 dark:bg-gray-800 dark:text-gray-400 dark:hover:border-gray-600"}`} type="button" key={option.value} onClick={() => onChange(option.value)}>{option.label}</button>
      ))}
    </div>
  );
}

export function IconButton({ children, className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-400 dark:text-gray-500 disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400 dark:disabled:border-gray-700 dark:disabled:bg-gray-800 ${className}`} type="button" {...props}>{children}</button>;
}
