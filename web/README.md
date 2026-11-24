# PULSE — Company Intelligence

PULSE is the React-based product interface for the E-Commerce ETL & Sales Analytics project. The existing Python/ DuckDB pipeline remains in the repository; this new interface is being built as the shareable product experience.

## Run the web application

Requirements: Node.js 20 or newer.

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000.

## Current capabilities

- Responsive SaaS-style workspace with overview, navigation and KPI cards.
- Interactive date-window and category filters.
- Revenue trend chart with sales/orders metric toggle.
- Category mix, product rankings, recent order table and calculated data observations.
- Search across order IDs, customers, products and cities.
- Upload CSV, Excel (.xlsx/.xls) or JSON files in the browser.
- Export the currently filtered rows to CSV.
- What-if control and deeper business workspaces are planned for subsequent iterations.

## Data handling

The first screen uses clearly labeled synthetic demonstration data. Uploaded files are parsed in the browser and replace the current in-memory view; files are not sent to a server or saved. The current single-file parser maps common sales fields. It does not yet perform a full multi-table relational model or guarantee that every source schema is interpreted correctly. Check the field mapping and data definitions before using results for business decisions.

## Architecture roadmap

- Frontend: Next.js, React, TypeScript, Recharts.
- Analytics API: Python + FastAPI.
- Storage/query layer: retain DuckDB for local analytical workloads; add PostgreSQL if persistent multi-user workspaces are needed.
- Deployment: web frontend and API deployed separately, with environment-based API configuration.

## AI analyst

The Ask PULSE panel answers questions using the currently filtered dataset, can propose a chart, and renders that chart on the dashboard. Conversation history is saved in the browser's local storage for later reference on the same browser/profile. It is not yet a cross-device or account-synced history.

To enable AI answers:

1. Copy `.env.example` to `.env.local` in the `web` folder.
2. Set `OPENAI_API_KEY` to your own API key and optionally set `OPENAI_MODEL`.
3. Restart `npm run dev`.

The key is read only by the Next.js server route at `/api/chat`; it is not sent to the browser. Do not commit `.env.local` or paste the key into chat.

The current AI context includes up to 250 rows from the active filtered view. The assistant explains this limitation and should not be treated as an audited financial system. More complete aggregation, saved named conversations, user accounts, and server-side dataset storage are planned for the FastAPI-backed release.
