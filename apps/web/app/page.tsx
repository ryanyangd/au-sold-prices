import Link from "next/link";
import { AddressSearch } from "@/components/AddressSearch";
import { USE_MOCK, ANNUAL_PER_MONTH, PRICING, SITE } from "@/lib/config";
import { btnPrimary, btnSecondary, card, container } from "@/lib/ui";

const FEATURES = [
  {
    title: "Government-sourced sales",
    body: "Built on official NSW property sales records, not scraped listings or estimates.",
    icon: "M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z",
  },
  {
    title: "Growth you can measure",
    body: "Annualised growth, holding period and how each sale compares with the suburb median.",
    icon: "M3 17l6-6 4 4 8-8M15 7h6v6",
  },
  {
    title: "Suburb context",
    body: "Medians, price ranges and 1, 3 and 5 year change for the same property type.",
    icon: "M3 21h18M5 21V8l7-4 7 4v13M9 21v-6h6v6",
  },
  {
    title: "Comparable sales",
    body: "See what similar nearby properties actually sold for, and jump straight to them.",
    icon: "M4 6h16M4 12h16M4 18h10",
  },
];

const STEPS = [
  { n: "1", title: "Search an address", body: "Start typing and pick your property from the suggestions." },
  { n: "2", title: "Review the history", body: "Check past sales, growth and how it compares with the suburb." },
  { n: "3", title: "Go deeper with Pro", body: "Unlock trend charts, price distribution and comparable sales." },
];

const FAQ = [
  {
    q: "Where does the data come from?",
    a: `${SITE.attribution}. We process it to make it searchable and comparable. Coverage starts in NSW.`,
  },
  {
    q: "Is this a valuation?",
    a: "No. AusSold shows historical sales and statistics only. It is not valuation advice and the data may be incomplete.",
  },
  {
    q: "What do I get on the Free plan?",
    a: "Address search, the last sale price and date, key growth metrics and a suburb snapshot. Pro adds full sale history, trend charts, price distribution and comparable sales.",
  },
  {
    q: "Can I cancel Pro?",
    a: "Yes. You can manage or cancel your subscription at any time from your account.",
  },
  {
    q: "Which states are covered?",
    a: "New South Wales to begin with. We plan to add more states over time.",
  },
];

export default function Home() {
  return (
    <>
      <section className="border-b border-line bg-gradient-to-b from-brand-soft/60 to-bg">
        <div className={`${container} py-16 text-center sm:py-24`}>
          <h1 className="mx-auto max-w-3xl text-4xl font-extrabold tracking-tight sm:text-5xl">
            What did it really sell for?
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted">
            Search any NSW address and see its sale history, growth and suburb trends, straight from government sales data.
          </p>
          <div className="mx-auto mt-8 max-w-2xl">
            <AddressSearch size="lg" />
          </div>
          {USE_MOCK && (
            <p className="mt-4 text-sm text-muted">
              Demo mode with synthetic data. Try “Example”, “Wattle” or “Harbour”.
            </p>
          )}
        </div>
      </section>

      <section aria-labelledby="features" className={`${container} py-16`}>
        <h2 id="features" className="text-center text-3xl font-bold tracking-tight">
          Trust the numbers
        </h2>
        <ul className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <li key={f.title} className={`${card} p-6`}>
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-soft text-brand">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d={f.icon} />
                </svg>
              </span>
              <h3 className="mt-4 font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-muted">{f.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="how" className="border-y border-line bg-surface">
        <div className={`${container} py-16`}>
          <h2 id="how" className="text-center text-3xl font-bold tracking-tight">
            How it works
          </h2>
          <ol className="mt-10 grid gap-8 md:grid-cols-3">
            {STEPS.map((s) => (
              <li key={s.n} className="text-center">
                <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-btn text-lg font-bold text-white">
                  {s.n}
                </span>
                <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="pricing" className={`${container} py-16`}>
        <div className="mx-auto max-w-3xl rounded-2xl border border-line bg-surface p-8 text-center shadow-sm sm:p-12">
          <h2 id="pricing" className="text-3xl font-bold tracking-tight">
            Free to search. Pro for the full picture.
          </h2>
          <p className="mt-3 text-muted">
            Pro is {PRICING.currencyLabel}
            {PRICING.proMonthly} a month, or {PRICING.currencyLabel}
            {PRICING.proAnnual} a year (just {PRICING.currencyLabel}
            {ANNUAL_PER_MONTH.toFixed(0)} a month).
          </p>
          <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/pricing" className={btnPrimary}>
              See pricing
            </Link>
            <Link href="/login" className={btnSecondary}>
              Get started free
            </Link>
          </div>
        </div>
      </section>

      <section aria-labelledby="faq" className="mx-auto w-full max-w-3xl px-4 pb-20 sm:px-6">
        <h2 id="faq" className="text-center text-3xl font-bold tracking-tight">
          Frequently asked questions
        </h2>
        <div className="mt-8 divide-y divide-line rounded-xl border border-line bg-surface">
          {FAQ.map((item) => (
            <details key={item.q} className="group p-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
                {item.q}
                <span aria-hidden="true" className="text-muted transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-muted">{item.a}</p>
            </details>
          ))}
        </div>
      </section>
    </>
  );
}
