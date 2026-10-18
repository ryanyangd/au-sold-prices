import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { SITE } from "@/lib/config";

export const metadata: Metadata = { title: "Privacy Policy (draft)" };

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy (draft)">
      <p>This draft describes how {SITE.name} intends to handle personal information. Final wording is to be confirmed.</p>
      <h2>Information we collect</h2>
      <p>Account details provided by your sign-in provider (name and email) and basic billing status.</p>
      <h2>How we use it</h2>
      <p>To provide the service, manage your plan and keep the product secure. We do not run advertising trackers.</p>
      <h2>Third parties</h2>
      <p>Sign-in and payment providers process data on our behalf. A full list will be published before launch.</p>
      <h2>Your rights</h2>
      <p>You will be able to access, correct or delete your information. Contact details to be confirmed.</p>
    </LegalPage>
  );
}
