#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p data/{db,events,clusters,artifacts,outbox/pending,outbox/sent,outbox/failed,logs,replay,tmp}
echo "Install complete."
echo "Next steps:"
echo "  1) Copy config/settings.example.yaml to /etc/rf-passive-recorder/settings.yaml"
echo "  2) Run: .venv/bin/rfpr init-db"
echo "  3) Run daemon: .venv/bin/rfpr run"
echo "  4) For systemd: sudo cp systemd/rf-passive-recorder.service /etc/systemd/system/"
