import { formatPropertyType } from "@/lib/format";
import type { PropertyType } from "@/lib/types";

const STYLES: Record<PropertyType, string> = {
  house: "bg-indigo-100 text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-200",
  unit: "bg-teal-100 text-teal-800 dark:bg-teal-500/20 dark:text-teal-200",
  "vacant land": "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-200",
  other: "bg-slate-200 text-slate-700 dark:bg-slate-500/25 dark:text-slate-200",
};

export function TypeBadge({ type }: { type: PropertyType }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[type] ?? STYLES.other}`}
    >
      {formatPropertyType(type)}
    </span>
  );
}
