import Link from "next/link";
import { SITE } from "@/lib/config";
import { container } from "@/lib/ui";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-line bg-surface">
      <div className={`${container} flex flex-col gap-6 py-10 text-sm text-muted`}>
        <div className="flex flex-col justify-between gap-4 sm:flex-row">
          <div>
            <p className="text-base font-bold text-fg">{SITE.name}</p>
            <p className="mt-1 max-w-sm">Sold-price analytics for Australian property.</p>
          </div>
          <nav aria-label="Footer" className="flex gap-6">
            <Link href="/pricing" className="hover:text-fg">
              Pricing
            </Link>
            <Link href="/terms" className="hover:text-fg">
              Terms
            </Link>
            <Link href="/privacy" className="hover:text-fg">
              Privacy
            </Link>
          </nav>
        </div>
        <div className="border-t border-line pt-6">
          <p>{SITE.attribution}.</p>
          <p className="mt-1">{SITE.disclaimer}</p>
          <p className="mt-3">© {new Date().getFullYear()} {SITE.name}. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
