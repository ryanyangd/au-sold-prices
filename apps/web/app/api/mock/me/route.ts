import { NextResponse } from "next/server";
import { emailFromRequest, meFor, mockDisabled, unauthorized } from "@/lib/mock/accounts";

export function GET(req: Request) {
  const off = mockDisabled();
  if (off) return off;
  const email = emailFromRequest(req);
  return email ? NextResponse.json(meFor(email)) : unauthorized();
}
