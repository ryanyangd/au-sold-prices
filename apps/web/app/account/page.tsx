import type { Metadata } from "next";
import { AccountPanel } from "@/components/AccountPanel";
import { container } from "@/lib/ui";

export const metadata: Metadata = { title: "Account" };

export default function AccountPage() {
  return (
    <div className={`${container} py-12`}>
      <AccountPanel />
    </div>
  );
}
