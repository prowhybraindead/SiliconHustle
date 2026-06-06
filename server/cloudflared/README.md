# Cloudflare Tunnel Runner

This folder contains the token-based Cloudflare Tunnel runner for Silicon Hustle.

The recommended deployment mode is:

- Cloudflare Pages hosts the frontend
- Cloudflare Zero Trust hosts the tunnel
- the backend stays private on `127.0.0.1:8000`
- the tunnel token lives in `game/server/cloudflared/.env`

## Setup

1. Create a tunnel in the Cloudflare Zero Trust dashboard.
2. Add a public hostname such as:
   - hostname: `api-your-domain.example`
   - service: `http://127.0.0.1:8000`
3. Copy the tunnel token from the dashboard.
4. Copy `.env.example` to `.env` and fill in `CLOUDFLARED_TOKEN`.
5. If you want the script to bootstrap `cloudflared` automatically when it is missing, keep `CLOUDFLARED_AUTO_INSTALL=1`.

## Run

```bash
chmod +x startwithtunnel.sh
./startwithtunnel.sh
```

You can also point the script at a different env file:

```bash
./startwithtunnel.sh ./prod.env
```

The runner uses:

```bash
cloudflared tunnel run --token "$CLOUDFLARED_TOKEN"
```

If `cloudflared` is not installed and `CLOUDFLARED_AUTO_INSTALL=1`, the script downloads a local copy into `game/server/cloudflared/.bin/` before starting the tunnel.

## Optional systemd example

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

If you want systemd to inject env vars too, you can add `EnvironmentFile=/path/to/Silicon-Hustle/game/server/cloudflared/.env`, but it is not required because the script loads `.env` itself.

## Troubleshooting

### Token missing

- Confirm `game/server/cloudflared/.env` exists
- Confirm `CLOUDFLARED_TOKEN` is set
- Do not place a real token in `.env.example`

### Binary missing

- Confirm `CLOUDFLARED_AUTO_INSTALL=1` is set if you want the script to fetch `cloudflared` automatically
- Make sure `curl` or `wget` is available
- If auto-install is disabled, install `cloudflared` manually or point `CLOUDFLARED_BIN` at an existing binary

### Backend not running

- Confirm the backend is listening on `127.0.0.1:8000`
- Check:

```bash
curl http://127.0.0.1:8000/health
```

### Cloudflare 502

- Confirm the public hostname target is `http://127.0.0.1:8000`
- Confirm the backend service is running
- Confirm the tunnel process is healthy

### CORS error

- Confirm backend `FRONTEND_ORIGIN` matches the deployed Cloudflare Pages domain
- Restart the backend after updating the env file

### Frontend still calls localhost

- Confirm Cloudflare Pages has `VITE_API_BASE_URL=https://api-your-domain.example`
- Redeploy the frontend after changing the env value
