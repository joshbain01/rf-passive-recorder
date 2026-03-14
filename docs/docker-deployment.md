# Docker Compose deployment on Raspberry Pi

This runbook installs `rf-passive-recorder` as a disposable Docker container with persistent host config/data.

## Deployment goals
- Keep host pollution low (Docker/Compose only).
- Persist config and runtime data on host.
- Keep runtime container disposable and easy to rebuild.
- Use RTL-SDR USB mapping without `privileged: true`:
  - `/dev/bus/usb:/dev/bus/usb`
  - `group_add: plugdev`

## Directory layout
Default location created by setup script:

```text
/opt/rf-passive-recorder/
├── compose.yml
├── Dockerfile
├── .env
├── config/
│   ├── settings.example.yaml
│   └── settings.yaml
├── data/
└── ... repo files
```

## One-time setup

```bash
git clone https://github.com/joshbain01/rf-passive-recorder.git
cd rf-passive-recorder
./setup_rfpr_docker.sh
```

What setup does:
1. Clones or updates repo at `/opt/rf-passive-recorder` (override with `RFPR_DEPLOY_DIR`).
2. Creates `config/` and `data/`.
3. Seeds `config/settings.yaml` from example when missing.
4. Sets container-safe defaults in seeded config:
   - `app.data_dir: /data`
   - `api.host: 0.0.0.0`
5. Creates `.env` from `.env.example` with current UID/GID.
6. Builds image and runs one-time `rfpr init-db`.

## Start / stop / rebuild

```bash
cd /opt/rf-passive-recorder
docker compose up -d
docker compose logs -f
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Validation

```bash
cd /opt/rf-passive-recorder
# 1) service status
docker compose ps

# 2) live logs
docker compose logs --tail=200

# 3) health endpoint (bound to localhost by default)
curl -fsS http://127.0.0.1:8787/healthz

# 4) trigger an event via API
curl -fsS -X POST http://127.0.0.1:8787/trigger

# 5) verify latest events
curl -fsS http://127.0.0.1:8787/events/latest | python3 -m json.tool
```

Optional synthetic generation inside container:

```bash
docker compose run --rm rf-passive-recorder test-synthetic --config /config/settings.yaml
```

## Upgrade workflow

```bash
cd /opt/rf-passive-recorder
git pull --ff-only
docker compose build
docker compose up -d
```

## Uninstall

```bash
cd /opt/rf-passive-recorder
./uninstall_rfpr_docker.sh
```

To also delete the local app image:

```bash
REMOVE_IMAGES=true ./uninstall_rfpr_docker.sh
```

This removes the deployment directory and app stack, while leaving Docker itself installed.

## Configuration notes
- Main config file: `/opt/rf-passive-recorder/config/settings.yaml`
- Persistent runtime files are under `/opt/rf-passive-recorder/data`.
- To expose API beyond localhost, edit `.env` (`RFPR_API_BIND=0.0.0.0`) and apply host firewall controls.
