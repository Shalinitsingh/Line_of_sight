# Line-of-Sight — Frontend (Next.js)

The web UI for the Line-of-Sight backend. Next.js (App Router) + TypeScript +
Tailwind. Matches the Figma: 60-30-10 palette, the Corporate/Hospital industry
toggle that drives the accent colour (amber vs teal), and the full auth +
email-verification flow.

## Prerequisites
- The backend running at `http://localhost:8000` (see the backend README / `docker compose up`).
- Node.js 18+ (you have 22).

## Run it

```bash
cd frontend
cp .env.local.example .env.local      # points at http://localhost:8000
npm install
npm run dev
```

Open **http://localhost:3000**.

> The backend already allows requests from `http://localhost:3000` and `:5173`
> (CORS). If you run the frontend on another port, add it to `CORS_ORIGINS` in the
> backend `.env`.

## Screens

| Route | Maps to | Backend endpoints |
|---|---|---|
| `/login` | LOG IN | `POST /auth/login` |
| `/signup` | SIGN UP ("We are Glad you are here") | `POST /auth/signup` (auto-creates org with chosen industry) |
| `/forgot-password` | Send Code → Set Password | `POST /auth/send-code`, `POST /auth/reset-password` |
| `/dashboard` | counts + recent activity | `GET /datasets`, `/reports`, `/audit` |
| `/datasets` | Data ingestion (CSV/Excel upload) | `POST /datasets`, `GET /datasets/{id}/columns` |
| `/ai-tracker` | Ask → Validate → Generate | `POST /metrics`, `/metrics/{id}/propose`, `/formulas/{id}/validate`, `/formulas/{id}/execute` |
| `/reports` | reports list + create | `GET/POST /reports` |
| `/about` | Explanations of Buttons | — |

## Email verification (how it works now)

The backend runs in **DEV email mode** unless SMTP is configured: verification
codes are logged to the API console and returned to the UI so you can complete the
flow with no email provider. The forgot-password screen displays the dev code
directly. To send real emails, set the `SMTP_*` vars in the backend `.env` — no
frontend change needed.

## Industry theme

The Corporate/Hospital toggle (on login/signup/about) sets `data-theme` on `<html>`
and is persisted. `--accent` switches between amber (`#C77F2E`) and teal
(`#3D7B7C`). On signup, the chosen industry is sent to the backend and stored on the
organization.

## Code style
ESLint (`next/core-web-vitals`) + Prettier (88-col), parallel to the backend's
flake8/black setup.

```bash
npm run lint
npx prettier --write src
```

## Not wired in this build
- **Google sign-in** — the button is present but disabled (OAuth is a separate setup).
- Token is stored in `localStorage`; for production, move to httpOnly cookies.
