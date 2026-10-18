"use client";

import Link from "next/link";
import { useState } from "react";
import { SITE } from "@/lib/config";
import { useAuth } from "@/lib/auth/context";
import { btnPrimary, container } from "@/lib/ui";
import { ThemeToggle } from "./ThemeToggle";

const navLink = "rounded-md px-3 py-2 text-sm font-medium text-muted hover:text-fg";

export function Header() {
  const { user, loading } = useAuth();
  const [open, setOpen] = useState(false);

  const links = (
    <>
      <Link href="/pricing" className={navLink} onClick={() => setOpen(false)}>
        Pricing
      </Link>
      {user ? (
        <Link href="/account" className={navLink} onClick={() => setOpen(false)}>
          Account
        </Link>
      ) : (
        <Link href="/login" className={navLink} onClick={() => setOpen(false)}>
          Sign in
        </Link>
      )}
    </>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur">
      <div className={`${container} flex h-16 items-center justify-between gap-4`}>
        <Link href="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <span
            aria-hidden="true"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-btn text-sm text-white"
          >
            A$
          </span>
          {SITE.name}
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 sm:flex">
          {links}
          {!user && !loading && (
            <Link href="/login" className={`${btnPrimary} ml-2 !py-2`}>
              Get started
            </Link>
          )}
          <span className="ml-2">
            <ThemeToggle />
          </span>
        </nav>

        <div className="flex items-center gap-2 sm:hidden">
          <ThemeToggle />
          <button
            type="button"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label="Menu"
            onClick={() => setOpen((o) => !o)}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-surface"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Mobile" className={`${container} flex flex-col gap-1 pb-4 sm:hidden`}>
          {links}
          {!user && !loading && (
            <Link href="/login" className={btnPrimary} onClick={() => setOpen(false)}>
              Get started
            </Link>
          )}
        </nav>
      )}
    </header>
  );
}
