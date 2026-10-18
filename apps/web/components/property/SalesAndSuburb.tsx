import { changeClass, formatCurrency, formatDate, formatPct, formatYears } from "@/lib/format";
import type { SaleRecord, SuburbSnapshot } from "@/lib/types";
import { Section } from "./Section";

export function SalesHistory({ sales }: { sales: SaleRecord[] }) {
  return (
    <Section title="Sale history">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[28rem] text-left text-sm">
          <caption className="sr-only">Previous sales of this property, newest first</caption>
          <thead className="text-muted">
            <tr className="border-b border-line">
              <th scope="col" className="py-2 pr-4 font-medium">Date</th>
              <th scope="col" className="py-2 pr-4 text-right font-medium">Price</th>
              <th scope="col" className="py-2 pr-4 text-right font-medium">Change</th>
              <th scope="col" className="py-2 text-right font-medium">Years held</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <tr key={`${s.contract_date}-${s.price}`} className="border-b border-line/60 last:border-0">
                <td className="py-3 pr-4">
                  <span className="font-medium">{formatDate(s.contract_date)}</span>
                  {s.settlement_date && (
                    <span className="block text-xs text-muted">Settled {formatDate(s.settlement_date)}</span>
                  )}
                </td>
                <td className="py-3 pr-4 text-right font-semibold">{formatCurrency(s.price)}</td>
                <td className={`py-3 pr-4 text-right ${changeClass(s.change_pct)}`}>{formatPct(s.change_pct)}</td>
                <td className="py-3 text-right">{formatYears(s.years_held)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function Change({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg bg-surface-2 px-3 py-2 text-center">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={`mt-0.5 text-sm font-semibold ${changeClass(value)}`}>{formatPct(value)}</dd>
    </div>
  );
}

export function SuburbSnapshotCard({ suburb }: { suburb: SuburbSnapshot }) {
  return (
    <Section title={`${suburb.name} snapshot`} subtitle={`${suburb.property_type} sales, last 12 months`}>
      <dl>
        <dt className="text-sm text-muted">Median price</dt>
        <dd className="text-3xl font-bold tracking-tight">{formatCurrency(suburb.median_12m)}</dd>
        <dd className="mt-1 text-sm text-muted">
          Middle half: {formatCurrency(suburb.p25_12m)} – {formatCurrency(suburb.p75_12m)}
        </dd>
        <dt className="mt-4 text-sm text-muted">Sales in last 12 months</dt>
        <dd className="text-lg font-semibold">{suburb.sales_12m}</dd>
      </dl>
      <dl className="mt-4 grid grid-cols-3 gap-2">
        <Change label="1 year" value={suburb.change_1y_pct} />
        <Change label="3 years" value={suburb.change_3y_pct} />
        <Change label="5 years" value={suburb.change_5y_pct} />
      </dl>
    </Section>
  );
}
