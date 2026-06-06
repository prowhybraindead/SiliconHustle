<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./public/logo/SilHus_W.svg">
    <source media="(prefers-color-scheme: light)" srcset="./public/logo/SilHus_B.svg">
    <img alt="Silicon Hustle wordmark" src="./public/logo/SilHus_W.svg" width="420px" />
  </picture>
</p>

<h1 align="center">Silicon Hustle</h1>

<p align="center">
  <strong>Tech Shop Simulator built as a full frontend + backend experience in one workspace.</strong><br />
  Buy low. Test hard. Sell smart.
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat" alt="MIT License" /></a>
  <img src="https://img.shields.io/badge/React-18.3-61DAFB?style=flat&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/Vite-5.4-646CFF?style=flat&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Cloudflare%20Pages-ready-F38020?style=flat&logo=cloudflare&logoColor=white" alt="Cloudflare Pages" />
</p>

---

## Overview

Silicon Hustle is a web-based tech shop management sim where you run a hardware business from the ground up.

The frontend is a cyber-industrial management console with dense telemetry panels, inventory views, quote workflows, staff management, and warranty operations.

The backend is a FastAPI service with SQLite persistence, rule-based gameplay systems, and deployment support for a private loopback-only production setup.

This repository includes both halves:

- `game/` contains the frontend app
- `game/server/` contains the backend API
- `game/server/cloudflared/` contains the token-based Cloudflare Tunnel runner
- `game/public/logo/` contains the logo assets used by the UI and README

---

## Game Loop

You manage a hardware showroom and service lab across multiple stations:

| Station | Purpose |
| :-- | :-- |
| `CMD` | Command center with cash, reputation, and telemetry |
| `CTL` | Product catalog and hardware reference data |
| `WRH` | Warehouse inventory management |
| `RFB` | Refurbish bench for cleaning, repair, and testing |
| `STF` | Staff hiring, morale, and assignment management |
| `WRN` | Warranty claims and resolution workflows |
| `FX` | Foreign exchange and pricing tools |
| `CHT` | Customer sales chat and quote negotiation |

The gameplay systems are intentionally rule-based so the data stays predictable, testable, and safe for persistence.

---

## Project Layout

```text
game/
  src/                  Frontend source code
  public/logo/          Brand wordmarks used by the UI
  server/               FastAPI backend
    app/                Backend package
    app.py              Fixed startup launcher for one-command hosts
    cloudflared/        Token-based tunnel runner
  docs/                 Deployment and operations docs
```

---

## Frontend

The frontend is a Vite app built with React 18, TypeScript, Tailwind, React Router, and TanStack Query.

### Local frontend setup

```bash
cd game
npm install
cp .env.example .env
npm run dev
```

- Dev server: `http://localhost:5173`
- Production build output: `dist`

### Frontend build

```bash
cd game
npm run build
```

### UI notes

- The app now uses logo wordmarks from `public/logo/` instead of text-only brand headers in the main shell, top bar, and home screen.
- The white logo is used on darker surfaces and the black logo is used on lighter surfaces through `<picture>` source switching.

---

## Backend

The backend lives in `game/server/` and serves the API on loopback in production.

### Local backend setup

```bash
cd game/server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

- Local API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

### Core backend settings

The most important environment values are:

- `DATABASE_URL=sqlite:///./silicon_hustle.db` for local development
- `DATABASE_URL=sqlite:////var/lib/silicon_hustle/silicon_hustle.db` for production
- `FRONTEND_ORIGIN` for the deployed frontend domain

### Fixed startup launcher

Some hosts only allow a single startup command. For that case, use:

```bash
/usr/local/bin/python /home/container/server/app.py
```

That launcher is designed to:

- start the backend from `game/server/app/`
- wait for `http://127.0.0.1:8000/health`
- start the token-based Cloudflare Tunnel runner
- stop the companion process if either side exits

---

## Cloudflare Deployment

The recommended production setup is:

Frontend on Cloudflare Pages
-> API domain on Cloudflare Tunnel
-> private FastAPI backend on `127.0.0.1:8000`
-> persistent SQLite file outside the repo tree

### Deployment docs

- [Cloudflare Tunnel Deployment Guide](./docs/DEPLOYMENT_TUNNEL.md)
- [Cloudflare Tunnel Runner](./server/cloudflared/README.md)

### Pages settings

- Root directory: `game`
- Build command: `npm run build`
- Output directory: `dist`
- Env:
  - `VITE_API_BASE_URL=https://api-your-domain.example`

### Tunnel runner

The tunnel runner is token-based. It expects:

- `game/server/cloudflared/.env`
- `CLOUDFLARED_TOKEN`
- optional `CLOUDFLARED_AUTO_INSTALL=1`

Run it with:

```bash
cd game/server/cloudflared
chmod +x startwithtunnel.sh
./startwithtunnel.sh
```

If `cloudflared` is missing and auto-install is enabled, the script downloads a local copy into `game/server/cloudflared/.bin/`.

---

## Persistence and Data

The backend stores the game state in SQLite and is designed to keep data stable across restarts and deploys.

Recommended production database path:

```text
/var/lib/silicon_hustle/silicon_hustle.db
```

Recommended production backend env:

```env
DATABASE_URL=sqlite:////var/lib/silicon_hustle/silicon_hustle.db
FRONTEND_ORIGIN=https://your-cloudflare-pages-domain.pages.dev
```

The SQLite database, PIN-based profile unlock logic, quote snapshots, market event snapshots, and warranty flow are all server-owned and intentionally isolated from the public frontend bundle.

---

## Useful Commands

### Frontend

```bash
cd game
npm run dev
npm run build
npm run preview
```

### Backend

```bash
cd game/server
pytest
python scripts/db_counts.py
python scripts/validate_brands.py
python scripts/validate_hardware_products.py --file data/imports/silicon_hustle_hardware_products_v2_normalized.json
```

### Tunnel runner

```bash
cd game/server/cloudflared
./startwithtunnel.sh
./startwithtunnel.sh ./prod.env
```

---

## Troubleshooting

- Frontend still calls `localhost`: check `VITE_API_BASE_URL` in Cloudflare Pages and redeploy.
- CORS errors: confirm `FRONTEND_ORIGIN` matches the deployed frontend domain and restart the backend.
- 502 from the tunnel: confirm backend is listening on `127.0.0.1:8000` and `curl http://127.0.0.1:8000/health` succeeds.
- Tunnel token missing: create `game/server/cloudflared/.env` from `.env.example`.
- Database looks empty: confirm `DATABASE_URL` points to the persistent SQLite file and the backend is using the intended env file.

If the tunnel token is ever exposed, rotate it in the Cloudflare dashboard immediately.

---

## More Docs

- [Backend README](./server/README.md)
- [Deployment Tunnel Guide](./docs/DEPLOYMENT_TUNNEL.md)
- [Cloudflare Tunnel Runner README](./server/cloudflared/README.md)
