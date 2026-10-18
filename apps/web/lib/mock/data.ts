/** Synthetic mock data (server-side only). All names, addresses and prices are invented. */
import type {
  AddressResult,
  Comparable,
  DistributionBucket,
  PropertyResponse,
  PropertyType,
  SaleRecord,
  SuburbSnapshot,
  TrendPoint,
} from "../types";

export const DATA_AS_OF = "2026-09-30";
const NOW = 119; // offset of 2026-09 from 2016-10
const TREND_FIRST = -201; // 2000-01
const TREND_START = { y: 2016, m: 10 };

interface SuburbDef {
  name: string;
  postcode: string;
  base: number; // house median at offset 0 (2016-10)
  growth: number; // annual
  phase: number;
  streets: string[];
}

const SUBURBS: SuburbDef[] = [
  { name: "Exampleville", postcode: "2000", base: 1_050_000, growth: 0.058, phase: 0.4, streets: ["Example St", "Sample Rd", "Placeholder Ave"] },
  { name: "Wattle Heights", postcode: "2001", base: 820_000, growth: 0.049, phase: 1.3, streets: ["Demo Cres", "Wattle Pl", "Testing Ln"] },
  { name: "Harbourview", postcode: "2002", base: 1_480_000, growth: 0.066, phase: 2.1, streets: ["Fiction Dr", "Mockingbird Ln", "Anchor St"] },
  { name: "Fernbrook", postcode: "2003", base: 690_000, growth: 0.044, phase: 2.9, streets: ["Fern Way", "Brook Rd", "Sample Ct"] },
  { name: "Quartz Bay", postcode: "2004", base: 930_000, growth: 0.053, phase: 3.7, streets: ["Quartz Pde", "Bay Tce", "Pebble St"] },
];

const TYPE_FACTOR: Record<PropertyType, number> = { house: 1, unit: 0.62, "vacant land": 0.55, other: 0.8 };
const ZONING: Record<PropertyType, string> = { house: "R2", unit: "R4", "vacant land": "R1", other: "B1" };
const TYPE_PLAN: PropertyType[] = ["house", "house", "house", "house", "unit", "unit", "vacant land", "other"];

function hash(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const round = (n: number, step: number) => Math.round(n / step) * step;

/** Median price index for a suburb/type at `offset` months from 2016-10 (may be negative). */
function priceAt(s: SuburbDef, type: PropertyType, offset: number): number {
  const noise = 0.04 * Math.sin(offset / 7 + s.phase) + 0.03 * Math.sin(offset / 3.1 + 2 * s.phase);
  return s.base * TYPE_FACTOR[type] * Math.exp((s.growth * offset) / 12 + noise);
}

function monthOffset(y: number, m: number): number {
  return (y - TREND_START.y) * 12 + (m - TREND_START.m);
}

function ymAt(offset: number): string {
  const total = TREND_START.y * 12 + (TREND_START.m - 1) + offset;
  const y = Math.floor(total / 12);
  return `${y}-${String((total % 12) + 1).padStart(2, "0")}`;
}

function isoToOffset(iso: string): number {
  const [y, m] = iso.split("-").map(Number);
  return monthOffset(y!, m!);
}

function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function yearsBetween(a: string, b: string): number {
  return (Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / (365.25 * 86400000);
}

interface MockProperty {
  id: string;
  suburb: SuburbDef;
  address: string;
  type: PropertyType;
  land: number | null;
  sales: { date: string; price: number; settle: string | null }[];
}

function build(): MockProperty[] {
  const out: MockProperty[] = [];
  SUBURBS.forEach((s, si) => {
    TYPE_PLAN.forEach((type, ti) => {
      const id = `${900 + si}-${100001 + ti * 7 + si * 100}`;
      const r = rng(hash(id));
      const street = s.streets[Math.floor(r() * s.streets.length)]!;
      const number = 1 + Math.floor(r() * 60);
      const unitPrefix = type === "unit" ? `${1 + Math.floor(r() * 12)}/` : "";
      const land =
        type === "unit" ? null : type === "vacant land" ? round(450 + r() * 600, 5) : round(280 + r() * 700, 5);
      const quality = 0.85 + r() * 0.3;
      const count = 1 + Math.floor(r() * 4);
      let year = 2000 + Math.floor(r() * 6);
      const sales: MockProperty["sales"] = [];
      for (let k = 0; k < count && year <= 2026; k++) {
        const month = 1 + Math.floor(r() * 12);
        const day = 1 + Math.floor(r() * 28);
        const date = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        if (date > "2026-08-31") break;
        const price = round(priceAt(s, type, isoToOffset(date)) * quality * (0.95 + r() * 0.1), 1000);
        sales.push({ date, price, settle: r() > 0.15 ? addDays(date, 42) : null });
        year += 2 + Math.floor(r() * 9);
      }
      if (sales.length === 0) {
        const date = "2019-05-14";
        sales.push({ date, price: round(priceAt(s, type, isoToOffset(date)) * quality, 1000), settle: addDays(date, 42) });
      }
      out.push({ id, suburb: s, address: `${unitPrefix}${number} ${street}`, type, land, sales });
    });
  });
  return out;
}

const PROPERTIES = build();
const BY_ID = new Map(PROPERTIES.map((p) => [p.id, p]));

const last = (p: MockProperty) => p.sales[p.sales.length - 1]!;
const display = (p: MockProperty) => `${p.address}, ${p.suburb.name} NSW ${p.suburb.postcode}`;

function toResult(p: MockProperty): AddressResult {
  return {
    property_id: p.id,
    address: p.address,
    suburb: p.suburb.name,
    postcode: p.suburb.postcode,
    state: "NSW",
    property_type: p.type,
    display: display(p),
    last_sale_price: last(p).price,
    last_sale_date: last(p).date,
  };
}

export function searchMock(q: string, limit: number): AddressResult[] {
  const tokens = q.toLowerCase().split(/[\s,]+/).filter(Boolean);
  if (tokens.join("").length < 3) return [];
  return PROPERTIES.filter((p) => {
    const hay = display(p).toLowerCase();
    return tokens.every((t) => hay.includes(t));
  })
    .sort((a, b) => {
      const pa = a.address.toLowerCase().startsWith(tokens[0]!) ? 0 : 1;
      const pb = b.address.toLowerCase().startsWith(tokens[0]!) ? 0 : 1;
      return pa - pb || a.address.localeCompare(b.address);
    })
    .slice(0, Math.max(1, Math.min(limit, 20)))
    .map(toResult);
}

function suburbSnapshot(s: SuburbDef, type: PropertyType): SuburbSnapshot {
  const now = NOW;
  const avg = Array.from({ length: 12 }, (_, i) => priceAt(s, type, now - i)).reduce((a, b) => a + b, 0) / 12;
  const change = (months: number) =>
    Math.round((priceAt(s, type, now) / priceAt(s, type, now - months) - 1) * 1000) / 10;
  return {
    name: s.name,
    state: "NSW",
    property_type: type,
    median_12m: round(avg, 1000),
    p25_12m: round(avg * 0.83, 1000),
    p75_12m: round(avg * 1.22, 1000),
    sales_12m: 40 + (hash(s.name + type) % 160),
    change_1y_pct: change(12),
    change_3y_pct: change(36),
    change_5y_pct: change(60),
  };
}

function trendFor(s: SuburbDef, type: PropertyType): TrendPoint[] {
  return Array.from({ length: NOW - TREND_FIRST + 1 }, (_, k) => {
    const i = TREND_FIRST + k;
    return {
      month: ymAt(i),
      median: round(priceAt(s, type, i), 1000),
      sales_count: 5 + (hash(`${s.name}${type}${i}`) % 26),
    };
  });
}

function distributionFor(median: number, sales: number): DistributionBucket[] {
  const width = round((median * 1.2) / 12, 25_000) || 25_000;
  const start = Math.max(0, round(median * 0.45, 25_000));
  const buckets = Array.from({ length: 14 }, (_, i) => {
    const from = start + i * width;
    const mid = from + width / 2;
    const z = (Math.log(mid) - Math.log(median)) / 0.32;
    return { bucket_from: from, bucket_to: from + width, weight: Math.exp(-0.5 * z * z) };
  });
  const total = buckets.reduce((a, b) => a + b.weight, 0);
  return buckets.map(({ bucket_from, bucket_to, weight }) => ({
    bucket_from,
    bucket_to,
    count: Math.round((weight / total) * sales),
  }));
}

function comparablesFor(p: MockProperty): Comparable[] {
  const others = PROPERTIES.filter((o) => o.id !== p.id);
  const score = (o: MockProperty) =>
    (o.suburb === p.suburb ? 0 : 2) + (o.type === p.type ? 0 : 1);
  return others
    .sort((a, b) => score(a) - score(b) || a.id.localeCompare(b.id))
    .slice(0, 6)
    .map((o) => ({
      property_id: o.id,
      address: display(o),
      property_type: o.type,
      price: last(o).price,
      contract_date: last(o).date,
      land_area_m2: o.land,
    }));
}

const ALL_SECTIONS = ["sales_history", "trend", "distribution", "comparables"];

export function getPropertyMock(id: string, plan: "free" | "pro"): PropertyResponse | null {
  const p = BY_ID.get(id);
  if (!p) return null;

  const snap = suburbSnapshot(p.suburb, p.type);
  const lastSale = last(p);
  const first = p.sales[0]!;
  const spanYears = yearsBetween(first.date, lastSale.date);
  const cagr =
    p.sales.length > 1 && spanYears > 0
      ? Math.round((Math.pow(lastSale.price / first.price, 1 / spanYears) - 1) * 1000) / 10
      : null;

  const sales: SaleRecord[] = p.sales
    .map((s, i): SaleRecord => {
      const prev = p.sales[i - 1];
      return {
        contract_date: s.date,
        settlement_date: s.settle,
        price: s.price,
        change_pct: prev ? Math.round((s.price / prev.price - 1) * 1000) / 10 : null,
        years_held: prev ? Math.round(yearsBetween(prev.date, s.date) * 10) / 10 : null,
      };
    })
    .reverse();

  const pro = plan === "pro";
  return {
    property: {
      id: p.id,
      address: p.address,
      suburb: p.suburb.name,
      postcode: p.suburb.postcode,
      state: "NSW",
      property_type: p.type,
      land_area_m2: p.land,
      zoning: ZONING[p.type],
      sale_count: p.sales.length,
    },
    metrics: {
      last_sale_price: lastSale.price,
      last_sale_date: lastSale.date,
      cagr_pct: cagr,
      holding_years: Math.round(yearsBetween(lastSale.date, DATA_AS_OF) * 10) / 10,
      vs_suburb_median_pct: snap.median_12m
        ? Math.round((lastSale.price / snap.median_12m - 1) * 1000) / 10
        : null,
    },
    suburb: snap,
    sales: pro ? sales : null,
    trend: pro ? trendFor(p.suburb, p.type) : null,
    distribution: pro ? distributionFor(snap.median_12m ?? lastSale.price, snap.sales_12m) : null,
    comparables: pro ? comparablesFor(p) : null,
    access: { plan, locked_sections: pro ? [] : ALL_SECTIONS },
    data_as_of: DATA_AS_OF,
  };
}
