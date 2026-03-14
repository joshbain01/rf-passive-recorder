# rf-passive-recorder

`rf-passive-recorder` is a Raspberry Pi friendly passive RF nuisance-event recorder for RTL-SDR devices. It captures trigger-centered windows, extracts non-identifying signal features, generates JSON payloads plus PNG artifacts, and groups recurring patterns into local deterministic clusters.

## What it does
- Passive capture from a configured fixed RF center frequency.
- Triggered event extraction with pre/post ring buffer windows.
- DSP feature extraction (STFT/PSD, burst timing, duty cycle, bandwidth, frequency behavior).
- Heuristic labels for broad behavior and morphology.
- Event JSON and cluster-summary JSON emission.
- Waterfall + PSD image artifacts.
- Local SQLite persistence + optional outbox/HTTP export.
- GPIO and software trigger support.
- Tiny localhost API for health + trigger + readback.

## What it explicitly does NOT do
- No geolocation, direction finding, triangulation, protocol decode, demodulation, decryption, threat-library matching, or exact emitter/device identification.
- No aircraft/location/route/crew/mission/operator-context fields.

## Requirements
- Raspberry Pi 4/5 (Pi 5 preferred)
- Debian/Raspberry Pi OS
- Python 3.11
- RTL-SDR + librtlsdr

## Installation
```bash
./install.sh
```
Then copy config:
```bash
sudo mkdir -p /etc/rf-passive-recorder
sudo cp config/settings.example.yaml /etc/rf-passive-recorder/settings.yaml
.venv/bin/rfpr init-db
```

## Configuration
- Config path default: `/etc/rf-passive-recorder/settings.yaml`
- Override: `rfpr run --config ./my.yaml`
- See `config/settings.example.yaml` for all fields and defaults.

## Running
### Daemon mode
```bash
.venv/bin/rfpr run --config /etc/rf-passive-recorder/settings.yaml
```

### One-shot synthetic mode
```bash
.venv/bin/rfpr test-synthetic
```

### Replay mode
```bash
.venv/bin/rfpr replay --input data/replay/example.c64
```

### API mode (local only)
```bash
.venv/bin/rfpr run --api-only
```
Endpoints:
- `GET /healthz`
- `POST /trigger`
- `GET /events/latest`
- `GET /events/{event_id}`
- `GET /clusters/{cluster_id}`

If `api.auth_token` is set, send `X-API-Token`.

## Triggering
- GPIO button: falling-edge button press with configurable debounce.
- Software trigger: `rfpr trigger` or `POST /trigger`.

## Data layout
`app.data_dir` includes:
- `db/recorder.sqlite3`
- `events/evt_*.json`
- `clusters/cluster_*.json`
- `artifacts/*_waterfall.png` + `*_psd.png`
- `outbox/pending|sent|failed`
- `logs/recorder.log`
- `replay/`, `tmp/`

## Payload schema notes
- UTC timestamps use ISO8601 with trailing `Z`.
- `time_utc` is trigger time.
- Metrics can be `null` when unavailable.
- `provenance` marks measured/derived/heuristic fields.

## Confidence and quality caveats
Confidence scores are deterministic and based on active-frame count, SNR, dropped sample condition, overload indication, and consistency checks.

Overload thresholds:
- >1% of raw IQ near full-scale (`|IQ| > 0.95`), or
- frequent near-saturation frame powers near 0 dBFS.

## Clustering
- Local deterministic weighted normalized Euclidean clustering.
- No scikit-learn.
- Cluster assignment by threshold; otherwise create new cluster.
- Cluster summary updated on every assignment.

## Troubleshooting
- SDR missing: app logs warning and uses synthetic fallback source.
- GPIO unavailable: safe when `gpio.enabled: false`.
- Artifact/export failures are logged; event processing continues.


## Docker Compose deployment (Raspberry Pi)
For a clean and reversible deployment, use Docker Compose instead of a host Python install.

```bash
./setup_rfpr_docker.sh
cd /opt/rf-passive-recorder
docker compose up -d
```

The Compose stack uses RTL-SDR USB mapping without `privileged`:
- `devices: /dev/bus/usb:/dev/bus/usb`
- `group_add: plugdev`

Config is persisted at `/opt/rf-passive-recorder/config/settings.yaml` and data at `/opt/rf-passive-recorder/data`.

Full runbook: `docs/docker-deployment.md`.

## systemd
```bash
sudo cp systemd/rf-passive-recorder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rf-passive-recorder
```

## Validation with synthetic signals
```bash
pytest -q
.venv/bin/rfpr test-synthetic
```
