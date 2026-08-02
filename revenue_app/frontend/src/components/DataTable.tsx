import { useMemo, useState } from "react";
import { displayCell, valueLabel } from "../format";
import type { ModuleTable } from "../types";

export function DataTables({ tables }: { tables: ModuleTable[] }) {
  const [active, setActive] = useState(0);
  const safeIndex = Math.min(active, Math.max(0, tables.length - 1));
  const table = tables[safeIndex];
  const columns = useMemo(() => table?.columns ?? [], [table]);
  if (!table) return null;

  return (
    <section className="bg-white dark:bg-gray-800 shadow-sm rounded-xl">
      <div className="px-5 pt-4 border-b border-gray-100 dark:border-gray-700/60 flex items-end gap-5" role="tablist">
        {tables.map((item, index) => (
          <button key={item.title} className={`flex h-11 items-center gap-2 border-b-2 text-sm font-medium ${index === safeIndex ? "border-violet-500 text-violet-500" : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"}`} onClick={() => setActive(index)}>{item.title}<span className="inline-flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full min-w-6 h-6 px-1 text-[10px] font-semibold text-gray-500 dark:text-gray-300">{item.rows.length}</span></button>
        ))}
      </div>
      <div className="p-3 overflow-x-auto">
        <table className="table-auto w-full dark:text-gray-300 tabular-nums">
          <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xs"><tr>{columns.map((column, index) => <th className="p-2" key={column}><div className={`font-semibold ${index ? "text-right" : "text-left"}`}>{valueLabel(column)}</div></th>)}</tr></thead>
          <tbody className="text-sm font-medium divide-y divide-gray-100 dark:divide-gray-700/60">
            {table.rows.map((row, index) => <tr key={String(row.id ?? row.period_label ?? row.day ?? index)}>{columns.map((column, columnIndex) => <td className="p-2 whitespace-nowrap" key={column}><div className={`${columnIndex ? "text-right" : "text-left"} text-gray-800 dark:text-gray-100`}>{displayCell(column, row[column])}</div></td>)}</tr>)}
          </tbody>
        </table>
      </div>
    </section>
  );
}
