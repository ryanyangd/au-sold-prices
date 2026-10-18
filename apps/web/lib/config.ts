import type { BillingPlan } from "./types";

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

const REAL_API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Base URL of the API; in mock mode the in-app route handlers stand in for it. */
export const API_BASE_URL = USE_MOCK ? "/api/mock" : REAL_API_BASE;

export const ENTRA = {
  clientId: process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID || "",
  authority: process.env.NEXT_PUBLIC_ENTRA_AUTHORITY || "",
  apiScope: process.env.NEXT_PUBLIC_ENTRA_API_SCOPE || "",
};

export const ENTRA_CONFIGURED = Boolean(ENTRA.clientId && ENTRA.authority && ENTRA.apiScope);

/** Dev auth is used in mock mode or whenever Entra is not configured. */
export const USE_DEV_AUTH = USE_MOCK || !ENTRA_CONFIGURED;

export const SEARCH = {
  minChars: 3,
  debounceMs: 150,
  limit: 8,
};

/** Single source of truth for plan pricing (A$). */
export const PRICING = {
  currency: "AUD",
  currencyLabel: "A$",
  proMonthly: 15,
  proAnnual: 144,
} as const;

export const PRICING_PLAN_IDS: Record<"monthly" | "annual", BillingPlan> = {
  monthly: "pro_monthly",
  annual: "pro_annual",
};

export const ANNUAL_SAVING = PRICING.proMonthly * 12 - PRICING.proAnnual;
export const ANNUAL_PER_MONTH = PRICING.proAnnual / 12;

export const SITE = {
  name: "AusSold",
  attribution: "Contains NSW Government property sales data",
  disclaimer: "Not valuation advice. Data may be incomplete.",
};

/** Identity-provider hints passed to Entra External ID. */
export const IDP_DOMAIN_HINTS = {
  google: "google.com",
  microsoft: "microsoft",
  facebook: "facebook.com",
} as const;
