import { NextResponse } from "next/server";
import { mockDisabled } from "@/lib/mock/accounts";

export function GET() {
  return mockDisabled() ?? NextResponse.json({ status: "ok" });
}
