"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { consumeReturnTo, PROVIDER_LABELS, safePath, setReturnTo, useAuth, type IdentityProvider } from "@/lib/auth/context";
import { btnSecondary, card } from "@/lib/ui";

const PROVIDERS: { id: IdentityProvider; badge: string; badgeClass: string }[] = [
  { id: "google", badge: "G", badgeClass: "bg-white text-red-500 ring-1 ring-line" },
  { id: "microsoft", badge: "M", badgeClass: "bg-sky-600 text-white" },
  { id: "facebook", badge: "f", badgeClass: "bg-blue-600 text-white" },
];

function LoginForm() {
  const { user, loading, mode, signIn } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = safePath(params.get("next"));
  const [devEmail, setDevEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<IdentityProvider | null>(null);

  useEffect(() => {
    if (user) router.replace(next ?? consumeReturnTo() ?? "/account");
  }, [user, next, router]);

  async function start(provider: IdentityProvider) {
    setError(null);
    setPending(provider);
    try {
      setReturnTo(next);
      await signIn(provider, { devEmail });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed. Please try again.");
      setPending(null);
    }
  }

  return (
    <div className={`${card} mx-auto w-full max-w-md p-8`}>
      <h1 className="text-2xl font-bold tracking-tight">Sign in to AusSold</h1>
      <p className="mt-2 text-sm text-muted">Choose an account to continue. We never post on your behalf.</p>

      <div className="mt-6 space-y-3">
        {PROVIDERS.map((p) => (
          <button
            key={p.id}
            type="button"
            disabled={loading || pending !== null}
            onClick={() => start(p.id)}
            className={`${btnSecondary} w-full !justify-start gap-3 !py-3`}
          >
            <span aria-hidden="true" className={`inline-flex h-6 w-6 items-center justify-center rounded text-sm font-bold ${p.badgeClass}`}>
              {p.badge}
            </span>
            {pending === p.id ? "Redirecting…" : `Continue with ${PROVIDER_LABELS[p.id]}`}
          </button>
        ))}
      </div>

      {error && (
        <p role="alert" className="mt-4 text-sm text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}

      {mode === "dev" && (
        <div className="mt-6 rounded-lg border border-dashed border-line p-3 text-sm">
          <p className="font-medium">Dev sign-in (no real accounts)</p>
          <label htmlFor="dev-email" className="mt-2 block text-muted">
            Optional email. Emails starting with “pro” start on the Pro plan in mock mode.
          </label>
          <input
            id="dev-email"
            type="email"
            value={devEmail}
            onChange={(e) => setDevEmail(e.target.value)}
            placeholder="pro.demo@example.com"
            className="mt-2 w-full rounded-lg border border-line bg-bg px-3 py-2"
          />
        </div>
      )}

      <p className="mt-6 text-xs text-muted">
        By continuing you agree to our <Link href="/terms" className="underline">Terms</Link> and{" "}
        <Link href="/privacy" className="underline">Privacy Policy</Link>.
      </p>
    </div>
  );
}

export function LoginPanel() {
  return (
    <Suspense fallback={<div className={`${card} mx-auto h-80 w-full max-w-md animate-pulse`} />}>
      <LoginForm />
    </Suspense>
  );
}
