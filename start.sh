#!/usr/bin/env bash
# Render deploy start script for CleanSlate backend
set -e

cd "$(dirname "$0")/backend"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
