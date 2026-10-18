import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { SITE } from "@/lib/config";

export const metadata: Metadata = { title: "Terms of Service (draft)" };

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service (draft)">
      <p>These draft terms will govern use of {SITE.name}. Final wording is to be confirmed.</p>
      <h2>1. The service</h2>
      <p>{SITE.name} provides property sold-price analytics derived from public data. Features depend on your plan.</p>
      <h2>2. No advice</h2>
      <p>{SITE.disclaimer} Nothing on this site is financial, legal or valuation advice.</p>
      <h2>3. Accounts and billing</h2>
      <p>Paid plans are billed in Australian dollars and can be cancelled at any time. Details to be confirmed.</p>
      <h2>4. Data sources</h2>
      <p>{SITE.attribution}.</p>
      <h2>5. Changes</h2>
      <p>We may update these terms. This placeholder will be replaced before launch.</p>
    </LegalPage>
  );
}
