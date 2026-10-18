import { card } from "@/lib/ui";

const bar = "animate-pulse rounded bg-surface-2";

export function PropertySkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading property" className="space-y-6">
      <div>
        <div className={`${bar} h-9 w-2/3 max-w-md`} />
        <div className={`${bar} mt-3 h-5 w-1/3 max-w-xs`} />
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={`${card} p-4`}>
            <div className={`${bar} h-4 w-24`} />
            <div className={`${bar} mt-3 h-8 w-32`} />
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className={`${card} h-64 p-5 lg:col-span-2`}>
          <div className={`${bar} h-full`} />
        </div>
        <div className={`${card} h-64 p-5`}>
          <div className={`${bar} h-full`} />
        </div>
      </div>
      <div className={`${card} h-80 p-5`}>
        <div className={`${bar} h-full`} />
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
