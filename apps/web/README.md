# AusSold web

Next.js (App Router, TypeScript strict) frontend for **au-sold-prices**: address search, property sold-price analytics, pricing/billing and account pages. Tailwind CSS, Recharts, vitest + Testing Library.

## Quick start (mock mode, no backend needed)

```bash
cd apps/web
npm install
npm run dev          # http://localhost:3000, mock API on by default
```

`npm run dev` loads `.env.development`, which sets `NEXT_PUBLIC_USE_MOCK=true`. All API contract endpoints are then served by in-app route handlers under `app/api/mock/*` with ~40 synthetic properties across 5 invented suburbs.

Try searching `example`, `wattle` or `harbour`.

### Mock accounts and plans

Mock mode (and any run without Entra settings) uses the **dev auth provider**: "Continue with Google/Microsoft/Facebook" creates a fake user in `localStorage` and uses the token `dev:<email>`.

- Default email is `dev.<provider>@example.com` (Free plan). On `/login` you can enter another email.
- Emails starting with `pro` (e.g. `pro.demo@example.com`) start on the **Pro** plan.
- Clicking **Upgrade to Pro** on `/pricing` calls the mock `POST /billing/checkout`, which returns a local URL that upgrades the account in server memory and redirects to `/account?mock=checkout`. State resets when the dev server restarts.
- Anonymous visitors are treated as Free: locked sections show blurred placeholders and an "Upgrade to Pro" call to action.

## Pointing at the real API

Set `NEXT_PUBLIC_USE_MOCK=false` (or leave it unset outside `npm run dev`) and set the API base URL, e.g. in `.env.local`:

```bash
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`lib/api.ts` is the only module that talks to the network. The mock route handlers return 404 unless `NEXT_PUBLIC_USE_MOCK=true`. The API must allow CORS from the web origin and the `Authorization` header.

## Environment variables

All `NEXT_PUBLIC_*` values are public and inlined at **build time**. Never put secrets in them.

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_USE_MOCK` | `true` in `npm run dev`, otherwise `false` | Serve the API from the in-app mock layer |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Real API base URL |
| `NEXT_PUBLIC_ENTRA_CLIENT_ID` | empty | Entra External ID app (client) ID |
| `NEXT_PUBLIC_ENTRA_AUTHORITY` | empty | Authority URL, e.g. `https://<tenant>.ciamlogin.com/<tenant-id>` |
| `NEXT_PUBLIC_ENTRA_API_SCOPE` | empty | API scope, e.g. `api://<api-client-id>/access_as_user` |

If the three Entra variables are all set and mock mode is off, `@azure/msal-browser` is used (redirect flow; redirect URI is `<origin>/login`, which must be registered in Entra). Otherwise the dev auth provider is used. Identity-provider hints (`domain_hint`) are `google.com`, `microsoft` and `facebook.com`; adjust them in `lib/config.ts` (`IDP_DOMAIN_HINTS`) to match your tenant setup.

## Structure

```
app/                 routes (/, /property/[id], /pricing, /login, /account, /terms, /privacy)
app/api/mock/        mock API route handlers (only active in mock mode)
components/          AddressSearch combobox, property sections, header/footer, pricing, account
lib/api.ts           the single typed API client
lib/config.ts        env, search settings and pricing constants (A$15/month, A$144/year)
lib/auth/            AuthProvider (dev + Entra) behind a common useAuth() interface
lib/mock/            synthetic data and in-memory mock accounts
```

Prices live in one place: `PRICING` in `lib/config.ts`.

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Dev server (mock mode by default) |
| `npm run build` | Production build (`output: "standalone"`) |
| `npm start` | Serve the production build |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | vitest (single run) |

To preview a production build against the mock layer: `NEXT_PUBLIC_USE_MOCK=true npm run build && npm start`.

## Docker

```bash
docker build -t aussold-web \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.example.com \
  --build-arg NEXT_PUBLIC_ENTRA_CLIENT_ID=... \
  --build-arg NEXT_PUBLIC_ENTRA_AUTHORITY=... \
  --build-arg NEXT_PUBLIC_ENTRA_API_SCOPE=... .
docker run -p 3000:3000 aussold-web
```

Multi-stage build, Next.js standalone output, runs as a non-root user on port 3000. Pass `--build-arg NEXT_PUBLIC_USE_MOCK=true` for a self-contained demo image.

## Notes

- Not valuation advice. The footer shows the data attribution ("Contains NSW Government property sales data") and disclaimer on every page.
- `/terms` and `/privacy` are draft placeholders.
- No analytics or trackers are included.
