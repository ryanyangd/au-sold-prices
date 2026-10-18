import type { Metadata } from "next";
import { LoginPanel } from "@/components/LoginPanel";
import { container } from "@/lib/ui";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className={`${container} py-14`}>
      <LoginPanel />
    </div>
  );
}
