"use client";

import { btnPrimary, card, container } from "@/lib/ui";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className={`${container} py-20`}>
      <div role="alert" className={`${card} mx-auto max-w-xl p-8 text-center`}>
        <h1 className="text-2xl font-bold">Something went wrong</h1>
        <p className="mt-2 text-muted">An unexpected error occurred. Please try again.</p>
        <button type="button" onClick={reset} className={`${btnPrimary} mt-6`}>
          Try again
        </button>
      </div>
    </div>
  );
}
