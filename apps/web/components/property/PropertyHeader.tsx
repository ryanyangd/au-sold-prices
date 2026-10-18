import { changeClass, formatArea, formatCurrency, formatDate, formatPct, formatYears } from "@/lib/format";
import type { PropertyInfo, PropertyMetrics } from "@/lib/types";
import { card } from "@/lib/ui";
import { TypeBadge } from "../TypeBadge";

export function PropertyHeader({ property, dataAsOf }: { property: PropertyInfo; dataAsOf: string }) {
  return (
    <header>
      <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{property.address}</h1>
      <p className="mt-1 text-lg text-muted">
        {property.suburb} {property.state} {property.postcode}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <TypeBadge type={property.property_type} />
        <span>
          <span className="text-muted">Land area: </span>
          {formatArea(property.land_area_m2)}
        </span>
        <span>
          <span className="text-muted">Zoning: </span>
          {property.zoning ?? "—"}
        </span>
        <span className="text-muted">Data as of {formatDate(dataAsOf)}</span>
      </div>
    </header>
  );
}

function Metric({
  label,
  value,
  sub,
  valueClass = "",
}: {
  label: string;
  value: string;
  sub?: string;
  valueClass?: string;
}) {
  return (
    <div className={`${card} p-4`}>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className={`mt-1 text-2xl font-bold tracking-tight ${valueClass}`}>{value}</dd>
      {sub && <dd className="mt-0.5 text-xs text-muted">{sub}</dd>}
    </div>
  );
}

export function MetricCards({ metrics, median }: { metrics: PropertyMetrics; median: number | null }) {
  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Metric label="Last sale price" value={formatCurrency(metrics.last_sale_price)} sub={formatDate(metrics.last_sale_date)} />
      <Metric
        label="Annualised growth (CAGR)"
        value={formatPct(metrics.cagr_pct)}
        valueClass={changeClass(metrics.cagr_pct)}
        sub={metrics.cagr_pct == null ? "Needs two or more sales" : "Per year, first to last sale"}
      />
      <Metric label="Holding period" value={formatYears(metrics.holding_years)} sub="Since last sale" />
      <Metric
        label="vs suburb median"
        value={formatPct(metrics.vs_suburb_median_pct)}
        valueClass={changeClass(metrics.vs_suburb_median_pct)}
        sub={median != null ? `Median ${formatCurrency(median)}` : undefined}
      />
    </dl>
  );
}
