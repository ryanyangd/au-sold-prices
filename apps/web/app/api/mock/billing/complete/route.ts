import { mockDisabled, setPro } from "@/lib/mock/accounts";

/** Stand-in for the payment provider's success redirect: upgrades the mock account. */
export function GET(req: Request) {
  const off = mockDisabled();
  if (off) return off;
  const email = new URL(req.url).searchParams.get("email")?.toLowerCase();
  if (email && /^[^@\s]+@[^@\s]+$/.test(email)) setPro(email);
  return new Response(null, { status: 303, headers: { Location: "/account?mock=checkout" } });
}
