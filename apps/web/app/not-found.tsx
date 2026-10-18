import Link from "next/link";
import { btnPrimary, card, container } from "@/lib/ui";

export default function NotFound() {
  return (
    <div className={`${container} py-20`}>
      <div className={`${card} mx-auto max-w-xl p-8 text-center`}>
        <h1 className="text-2xl font-bold">Page not found</h1>
        <p className="mt-2 text-muted">The page you’re looking for doesn’t exist.</p>
        <Link href="/" className={`${btnPrimary} mt-6`}>
          Back to home
        </Link>
      </div>
    </div>
  );
}
