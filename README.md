<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./public/logo/SilHus_W.svg">
    <source media="(prefers-color-scheme: light)" srcset="./public/logo/SilHus_B.svg">
    <img alt="Silicon Hustle Logo" src="./public/logo/SilHus_W.svg" width="380px" />
  </picture>
</p>

<h1 align="center">Silicon Hustle: Tech Shop Simulator</h1>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat" alt="License MIT" /></a>
  <img src="https://img.shields.io/badge/React-18.3-61DAFB?style=flat&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/Vite-5.4-646CFF?style=flat&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLite-3.x-003B57?style=flat&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Tests-95%20Passed-brightgreen?style=flat&logo=pytest&logoColor=white" alt="Tests" />
</p>

<p align="center">
  <strong>Simulate the operation of a PC component showroom & hardware refurbish lab.</strong><br />
  Slogan: <em>"Buy low. Test hard. Sell smart."</em>
</p>

---

## 🖥️ Project Overview

**Silicon Hustle** is a web-based tech shop management simulation game. Players assume the role of a hardware business owner: procuring used and new parts, running detailed hardware telemetry diagnostics, cleaning and refurbishing broken components, negotiating custom sales quotes with customers via chat, and hiring/managing technicians.

The client UI is built with a custom **Cyber-Industrial Game Console** aesthetic, featuring dense information panels, telemetry readouts, dark mode-first visuals, and tactile monospaced terminal logs.

---

## 🛠️ Feature Map (Stations)

| Station / Module | Description & Key Operational Mechanics |
| :--- | :--- |
| **CMD // Command Center** | Financial statistics, transaction log stream, 2D showroom board layout, and active telemetry stats. |
| **CTL // Catalog Vault** | Detailed hardware databases listing sockets, TDP values, MSRPs, and market volatility scales. |
| **WRH // Warehouse** | Central repository inventory. Shows known component metrics, wear telemetry, and defects. |
| **RFB // Refurbish Bench** | Cleaning dust, thermal paste re-application, fan replacements, firmware flashing, and micro-soldering. |
| **STF // Staff Room** | Hire/fire staff, monitor employee fatigue & morale levels, and assign technicians to different benches. |
| **WRN // Warranty Desk** | Resolve customer RMA/warranty tickets. Inspect hardware defects and issue repairs, swaps, or refunds. |
| **FX // FX Exchange** | Real-time foreign exchange market with 10 currencies. Tracks snapshots, spreads, and exchange fees. |
| **CHT // Sales Chat** | Script-driven negotiation desk. Customize quotes, analyze risk profiles, and seal customer orders. |

---

## 📦 Installation & Local Setup

### 1. Frontend Setup (React + Vite)

Navigate into the frontend project root:
```bash
cd game
npm install
cp .env.example .env
npm run dev
```
- **Local Dev Server:** `http://localhost:5173`

### 2. Backend Setup (FastAPI + SQLite)

Navigate to the backend server folder:
```bash
cd game/server
python -m venv .venv

# On Windows (PowerShell or CMD):
.venv\Scripts\activate

# On macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
- **Backend API URL:** `http://localhost:8000`
- **Swagger Documentation:** `http://localhost:8000/docs`

---

## 🔒 Testing & Data Validation

Silicon Hustle integrates testing and consistency validation utility scripts:

```bash
cd game/server

# Run the complete unit test suite (95 tests)
python -m pytest

# Display row metrics for SQLite records
python scripts/db_counts.py

# Verify master brand assets consistency
python scripts/validate_brands.py

# Import and validate hardware catalog data v2
python scripts/validate_hardware_products.py --file data/imports/silicon_hustle_hardware_products_v2_normalized.json
```

---

## 🌐 Deployment Guidelines (Deploy Readiness)

### Frontend (e.g., Cloudflare Pages)
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Root Directory:** `game`
- **Environment Variables:** Set `VITE_API_BASE_URL` to point to the production API domain (do not leave it as localhost).

### Backend (e.g., VPS / Ubuntu Server)
1. **Virtual Environment Setup:** Activate virtualenv and install dependencies from `requirements.txt`.
2. **Environment Settings (`.env`):**
   - Set `ENVIRONMENT=production`.
   - Set `DATABASE_URL` to an absolute file path pointing to persistent SQLite storage (e.g., `sqlite:////var/lib/silicon_hustle/production.db`).
   - Configure `FRONTEND_ORIGIN` to match your production frontend domain (e.g., Cloudflare Pages domain) to enforce strict CORS access.
3. **Operational Hosting:** Run backend with `uvicorn` or `gunicorn` behind an Nginx/Caddy reverse proxy configured with SSL certificates.

---

## ⚠️ Security & Database Regulations

> [!IMPORTANT]
> - **Idempotent Seeding:** Do not delete `silicon_hustle.db` when updating/deploying. The seed process is fully idempotent and protects user progress data.
> - **Hashed Profiles:** Profile authorization PIN codes and session tokens are encrypted using SHA-256 on the backend server. The `X-Profile-Unlock-Token` is strictly required for editing protected states.
> - **Hidden Condition attributes:** Wear attributes, sub-defects, and raw condition payload (`hidden_condition_json`) are private and strictly sanitized before responses reach the frontend.
> - **Git Checks:** Make sure SQLite databases (`*.db`, `*.sqlite`, `*.sqlite3`) and local `.env` keys are untracked by Git.

---

## 📄 License
Licensed under the **MIT License**. See [LICENSE](./LICENSE) for details.
