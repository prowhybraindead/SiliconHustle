# Silicon Hustle Deployment Guide

This guide describes the recommended production deployment for **Silicon Hustle** using:

- Cloudflare Pages for the frontend
- a private FastAPI backend bound to `127.0.0.1:8000`
- a token-based Cloudflare Tunnel (`cloudflared`)
- persistent SQLite storage outside the repo tree

The recommended tunnel flow is token-based only. Do not use local `credentials-file`, `config.yml`, `cloudflared tunnel login`, `cloudflared tunnel create`, or DNS route commands on the server for this setup.

---

## Architecture

```text
Cloudflare Pages frontend
  -> VITE_API_BASE_URL=https://api-your-domain.example
  -> Cloudflare Tunnel public hostname
  -> http://127.0.0.1:8000
  -> FastAPI backend
  -> persistent SQLite DB
```

### Security goals

- No public backend port is opened.
- Uvicorn listens only on loopback.
- Cloudflare handles the public hostname and TLS.
- Tunnel credentials stay in the Cloudflare dashboard token, not in a local config file.

---

## 1. Frontend Deployment

Deploy the Vite app to Cloudflare Pages.

### Build settings

- Root directory: `game`
- Build command: `npm run build`
- Output directory: `dist`

### Frontend environment

Set the API base URL in Cloudflare Pages:

```env
VITE_API_BASE_URL=https://api-your-domain.example
```

After changing the Pages environment variables, redeploy the site so the compiled assets pick up the new API domain.

---

## 2. Backend Service

Run the backend locally on the server and bind it to loopback.

### Persistent database directory

```bash
sudo mkdir -p /var/lib/silicon_hustle
sudo chown -R <deploy-user>:<deploy-user> /var/lib/silicon_hustle
```

### Backend environment example

Use a production `.env` file for the backend, for example `game/server/.env`:

```env
DATABASE_URL=sqlite:////var/lib/silicon_hustle/silicon_hustle.db
FRONTEND_ORIGIN=https://your-cloudflare-pages-domain.pages.dev
```

Keep other backend settings in the existing server env file as needed, but make sure the database path points to the persistent location above.

### Manual backend start

```bash
cd /path/to/Silicon-Hustle/game/server
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### systemd backend unit

Example `/etc/systemd/system/silicon-hustle.service`:

```ini
[Unit]
Description=Silicon Hustle FastAPI Backend
After=network.target

[Service]
User=deploy-user
Group=deploy-user
WorkingDirectory=/path/to/Silicon-Hustle/game/server
ExecStart=/path/to/Silicon-Hustle/game/server/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/path/to/Silicon-Hustle/game/server/.env

[Install]
WantedBy=multi-user.target
```

Enable it with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable silicon-hustle
sudo systemctl start silicon-hustle
sudo systemctl status silicon-hustle
```

### Fixed container startup entrypoint

If your host requires a single startup command, point it at the backend launcher:

```bash
/usr/local/bin/python /home/container/server/app.py
```

That launcher:

- loads `game/server/.env` for backend settings
- runs the backend from `game/server/app/`
- waits for `http://127.0.0.1:8000/health`
- starts `game/server/cloudflared/startwithtunnel.sh`
- stops the other process if either backend or tunnel exits

Use this when the platform only lets you choose one startup command and you want backend plus tunnel to come up together.

---

## 3. Token-Based Cloudflare Tunnel

Use the Cloudflare dashboard to create the tunnel and generate the connector token.

### Dashboard setup

1. Open the Cloudflare Zero Trust dashboard.
2. Create a new tunnel.
3. Add a public hostname such as:
   - hostname: `api-your-domain.example`
   - service: `http://127.0.0.1:8000`
4. Copy the tunnel token from the dashboard.

### Local runner files

Use the token runner in `game/server/cloudflared/`:

- `game/server/cloudflared/.env.example`
- `game/server/cloudflared/startwithtunnel.sh`
- `game/server/cloudflared/README.md`

Create `game/server/cloudflared/.env` from the example file and set the tunnel token there. Do not commit the real `.env`.

### Run the tunnel runner

```bash
cd /path/to/Silicon-Hustle/game/server/cloudflared
chmod +x startwithtunnel.sh
./startwithtunnel.sh
```

You can also point it at another env file:

```bash
./startwithtunnel.sh ./prod.env
```

The script starts Cloudflare Tunnel with:

```bash
cloudflared tunnel run --token "$CLOUDFLARED_TOKEN"
```

### Optional systemd tunnel unit

Example `/etc/systemd/system/silicon-hustle-tunnel.service`:

```ini
[Unit]
Description=Silicon Hustle Cloudflare Tunnel
After=network.target silicon-hustle.service
Requires=silicon-hustle.service

[Service]
User=deploy-user
Group=deploy-user
WorkingDirectory=/path/to/Silicon-Hustle/game/server/cloudflared
ExecStart=/path/to/Silicon-Hustle/game/server/cloudflared/startwithtunnel.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

If you prefer, you can also set `EnvironmentFile=/path/to/Silicon-Hustle/game/server/cloudflared/.env`, but it is not required because the script loads `.env` itself.

---

## 4. Verification Checklist

1. Open the public API hostname and confirm requests hit `https://api-your-domain.example`.
2. Check the backend directly on the server:

```bash
curl http://127.0.0.1:8000/health
```

3. Confirm the tunnel service is healthy.
4. Confirm the backend is running on loopback only.
5. Confirm the frontend uses the Pages `VITE_API_BASE_URL` value and not `localhost`.
6. Confirm `FRONTEND_ORIGIN` matches the deployed Cloudflare Pages domain.

---

## 5. Troubleshooting

### Tunnel returns 502

Likely causes:

- backend is not running
- backend is not listening on `127.0.0.1:8000`
- the Cloudflare public hostname points to the wrong local service target
- the tunnel cannot reach the backend process

Check the backend directly:

```bash
curl http://127.0.0.1:8000/health
```

### Tunnel script says token missing

Make sure `game/server/cloudflared/.env` exists and contains:

```env
CLOUDFLARED_TOKEN=replace-with-your-cloudflare-tunnel-token
CLOUDFLARED_AUTO_INSTALL=1
```

Do not add a real token to `.env.example`.
When `CLOUDFLARED_AUTO_INSTALL=1`, the runner downloads `cloudflared` into `game/server/cloudflared/.bin/` if the binary is missing.

### Frontend still calls localhost

Likely causes:

- `VITE_API_BASE_URL` was not set in Cloudflare Pages
- the site was not redeployed after the env change

Update the Pages env and redeploy.

### CORS error in the browser

Likely causes:

- backend `FRONTEND_ORIGIN` does not match the deployed Pages domain
- backend was not restarted after the env change

Update the backend env and restart the service.

### Database looks empty

Likely causes:

- the backend is pointing at the wrong `DATABASE_URL`
- the persistent SQLite file is not mounted or writable

Check counts from the backend folder:

```bash
cd game/server
python scripts/db_counts.py
```

### Token leaked to git

If a tunnel token is ever committed by mistake:

- confirm `game/server/cloudflared/.env` stays ignored
- rotate the tunnel token in the Cloudflare dashboard
