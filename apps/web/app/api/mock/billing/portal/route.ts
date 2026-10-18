import { NextResponse } from "next/server";
import { emailFromRequest, mockDisabled, unauthorized } from "@/lib/mock/accounts";

export function POST(req: Request) {
  const off = mockDisabled();
  if (off) return off;
  return emailFromRequest(req) ? NextResponse.json({ url: "/account?mock=portal" }) : unauthorized();
}
