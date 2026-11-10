#!/usr/bin/env bash
set -e
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
exec python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5190
