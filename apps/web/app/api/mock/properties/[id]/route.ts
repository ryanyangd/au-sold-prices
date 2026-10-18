import { NextResponse } from "next/server";
import { emailFromRequest, mockDisabled, planFor } from "@/lib/mock/accounts";
import { getPropertyMock } from "@/lib/mock/data";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const off = mockDisabled();
  if (off) return off;
  const { id } = await ctx.params;
  const data = getPropertyMock(id, planFor(emailFromRequest(req)));
  if (!data) return NextResponse.json({ detail: "Property not found" }, { status: 404 });
  await new Promise((r) => setTimeout(r, 250)); // simulate latency
  return NextResponse.json(data);
}
