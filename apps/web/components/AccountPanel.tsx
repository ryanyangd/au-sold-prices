"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";
import { ApiError, createPortal, getMe } from "@/lib/api";
import { useAuth } from "@/lib/auth/context";
import type { Me } from "@/lib/types";
import { btnPrimary, btnSecondary, card } from "@/lib/ui";

interface Loaded {
  key: string;
  me?: Me;
  error?: ApiError;
}

const STATUS_LABEL: Record<Me["status"], string> = {
  active: "Active",
  past_due: "Payment past due",
  canceled: "Canceled",
  none: "No subscription",
};

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 py-3 sm:flex-row sm:justify-between">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  );
}

function AccountInner() {
  const { user, token, loading, signOut } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const mock = params.get("mock");
  const [state, setState] = useState<Loaded | null>(null);
  const [retry, setRetry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const key = `${token ?? ""}|${retry}`;

  useEffect(() => {
    if (!token) return;
    const ctrl = new AbortController();
    getMe(token, ctrl.signal)
      .then((me) => !ctrl.signal.aborted && setState({ key, me }))
      .catch((e) => {
        if (!ctrl.signal.aborted) setState({ key, error: e instanceof ApiError ? e : new ApiError(0, "Something went wrong.") });
      });
    return () => ctrl.abort();
  }, [token, key]);

  async function manageBilling() {
    if (!token) return;
    setBusy(true);
    setActionError(null);
    try {
      const { url } = await createPortal(token);
      window.location.assign(url);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Couldn’t open the billing portal.");
      setBusy(false);
    }
  }

  async function handleSignOut() {
    await signOut();
    router.push("/");
  }

  if (loading) return <div className={`${card} mx-auto h-72 w-full max-w-2xl animate-pulse`} role="status" aria-label="Loading account" />;

  if (!user) {
    return (
      <div className={`${card} mx-auto max-w-xl p-8 text-center`}>
        <h1 className="text-2xl font-bold">You’re signed out</h1>
        <p className="mt-2 text-muted">Sign in to see your account and plan.</p>
        <Link href="/login?next=/account" className={`${btnPrimary} mt-6`}>Sign in</Link>
      </div>
    );
  }

  const current = state && state.key === key ? state : null;
  const me = current?.me;

  return (
    <div className="mx-auto w-full max-w-2xl space-y-4">
      <h1 className="text-3xl font-bold tracking-tight">Account</h1>

      {mock === "checkout" && (
        <p role="status" className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-200">
          Mock checkout complete. No payment was taken.
        </p>
      )}
      {mock === "portal" && (
        <p role="status" className="rounded-lg border border-line bg-surface-2 px-4 py-3 text-sm">
          Mock billing portal: this is where the payment provider’s portal would open.
        </p>
      )}

      <section className={`${card} p-6`} aria-busy={!current}>
        {!current && <div role="status" aria-label="Loading profile" className="h-32 animate-pulse rounded bg-surface-2" />}

        {current?.error && (
          <div role="alert">
            <p className="text-rose-600 dark:text-rose-400">
              {current.error.status === 401 ? "Your session has expired. Please sign in again." : current.error.message}
            </p>
            <div className="mt-4 flex gap-3">
              {current.error.status !== 401 && (
                <button type="button" className={btnSecondary} onClick={() => setRetry((r) => r + 1)}>Try again</button>
              )}
              <button type="button" className={btnPrimary} onClick={handleSignOut}>Sign out</button>
            </div>
          </div>
        )}

        {me && (
          <>
            <dl className="divide-y divide-line">
              <Row label="Name">{me.name}</Row>
              <Row label="Email">{me.email}</Row>
              <Row label="Plan">
                <span className={`rounded-full px-2.5 py-0.5 text-sm font-semibold ${me.plan === "pro" ? "bg-brand-soft text-brand" : "bg-surface-2"}`}>
                  {me.plan === "pro" ? "Pro" : "Free"}
                </span>
              </Row>
              <Row label="Subscription">{STATUS_LABEL[me.status]}</Row>
            </dl>

            {actionError && <p role="alert" className="mt-4 text-sm text-rose-600 dark:text-rose-400">{actionError}</p>}

            <div className="mt-6 flex flex-wrap gap-3">
              {me.plan === "pro" || me.status !== "none" ? (
                <button type="button" onClick={manageBilling} disabled={busy} className={btnPrimary}>
                  {busy ? "Opening…" : "Manage billing"}
                </button>
              ) : (
                <Link href="/pricing" className={btnPrimary}>Upgrade to Pro</Link>
              )}
              <button type="button" onClick={handleSignOut} className={btnSecondary}>Sign out</button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

export function AccountPanel() {
  return (
    <Suspense fallback={<div className={`${card} mx-auto h-72 w-full max-w-2xl animate-pulse`} />}>
      <AccountInner />
    </Suspense>
  );
}
