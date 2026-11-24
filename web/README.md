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
