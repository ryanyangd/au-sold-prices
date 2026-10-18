export type PropertyType = "house" | "unit" | "vacant land" | "other";
export type Plan = "free" | "pro";
export type SubscriptionStatus = "active" | "past_due" | "canceled" | "none";
export type BillingPlan = "pro_monthly" | "pro_annual";
export type SectionKey = "sales_history" | "trend" | "distribution" | "comparables";

export interface AddressResult {
  property_id: string;
  address: string;
  suburb: string;
  postcode: string;
  state: string;
  property_type: PropertyType;
  display: string;
  last_sale_price: number | null;
  last_sale_date: string | null;
}

export interface SearchResponse {
  results: AddressResult[];
}

export interface PropertyInfo {
  id: string;
  address: string;
  suburb: string;
  postcode: string;
  state: string;
  property_type: PropertyType;
  land_area_m2: number | null;
  zoning: string | null;
  sale_count: number;
}

export interface PropertyMetrics {
  last_sale_price: number;
  last_sale_date: string;
  cagr_pct: number | null;
  holding_years: number | null;
  vs_suburb_median_pct: number | null;
}

export interface SuburbSnapshot {
  name: string;
  state: string;
  property_type: PropertyType;
  median_12m: number | null;
  p25_12m: number | null;
  p75_12m: number | null;
  sales_12m: number;
  change_1y_pct: number | null;
  change_3y_pct: number | null;
  change_5y_pct: number | null;
}

export interface SaleRecord {
  contract_date: string;
  settlement_date: string | null;
  price: number;
  change_pct: number | null;
  years_held: number | null;
}

export interface TrendPoint {
  month: string;
  median: number;
  sales_count: number;
}

export interface DistributionBucket {
  bucket_from: number;
  bucket_to: number;
  count: number;
}

export interface Comparable {
  property_id: string;
  address: string;
  property_type: PropertyType;
  price: number;
  contract_date: string;
  land_area_m2: number | null;
}

export interface PropertyAccess {
  plan: Plan;
  locked_sections: string[];
}

export interface PropertyResponse {
  property: PropertyInfo;
  metrics: PropertyMetrics;
  suburb: SuburbSnapshot;
  sales: SaleRecord[] | null;
  trend: TrendPoint[] | null;
  distribution: DistributionBucket[] | null;
  comparables: Comparable[] | null;
  access: PropertyAccess;
  data_as_of: string;
}

export interface Me {
  id: string;
  email: string;
  name: string;
  plan: Plan;
  status: SubscriptionStatus;
}

export interface UrlResponse {
  url: string;
}
