import { NextResponse } from "next/server";
import { mockDisabled } from "@/lib/mock/accounts";
import { searchMock } from "@/lib/mock/data";

export async function GET(req: Request) {
  const off = mockDisabled();
  if (off) return off;
  const url = new URL(req.url);
  const q = url.searchParams.get("q") ?? "";
  const limit = Number(url.searchParams.get("limit")) || 8;
  await new Promise((r) => setTimeout(r, 120)); // simulate latency
  return NextResponse.json({ results: searchMock(q, limit) });
}
