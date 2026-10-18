import { NextResponse } from "next/server";
import { emailFromRequest, mockDisabled, unauthorized } from "@/lib/mock/accounts";

export async function POST(req: Request) {
  const off = mockDisabled();
  if (off) return off;
  const email = emailFromRequest(req);
  if (!email) return unauthorized();
  const body = (await req.json().catch(() => null)) as { plan?: string } | null;
  if (body?.plan !== "pro_monthly" && body?.plan !== "pro_annual") {
    return NextResponse.json({ detail: "Invalid plan" }, { status: 422 });
  }
  const params = new URLSearchParams({ email, plan: body.plan });
  return NextResponse.json({ url: `/api/mock/billing/complete?${params}` });
}
