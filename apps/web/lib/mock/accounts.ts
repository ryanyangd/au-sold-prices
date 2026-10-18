/** In-memory mock accounts (server-side only; resets on server restart). */
import { NextResponse } from "next/server";
import { USE_MOCK } from "../config";
import type { Me, Plan, SubscriptionStatus } from "../types";

interface Account {
  plan: Plan;
  status: SubscriptionStatus;
}

const g = globalThis as unknown as { __mockAccounts?: Map<string, Account> };
const accounts = (g.__mockAccounts ??= new Map<string, Account>());

export function mockDisabled(): NextResponse | null {
  return USE_MOCK ? null : NextResponse.json({ detail: "Not found" }, { status: 404 });
}

export function emailFromRequest(req: Request): string | null {
  const m = /^Bearer dev:(.+@.+)$/i.exec(req.headers.get("authorization") ?? "");
  return m ? m[1]!.toLowerCase() : null;
}

function account(email: string): Account {
  let a = accounts.get(email);
  if (!a) {
    // Emails starting with "pro" start on the Pro plan (handy for demos).
    a = email.startsWith("pro") ? { plan: "pro", status: "active" } : { plan: "free", status: "none" };
    accounts.set(email, a);
  }
  return a;
}

export function planFor(email: string | null): Plan {
  return email ? account(email).plan : "free";
}

export function setPro(email: string): void {
  accounts.set(email, { plan: "pro", status: "active" });
}

export function meFor(email: string): Me {
  const { plan, status } = account(email);
  return { id: `mock-${email}`, email, name: email.split("@")[0]!, plan, status };
}

export const unauthorized = () => NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
