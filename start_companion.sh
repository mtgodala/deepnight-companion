#!/usr/bin/env sh
# Deepnight Companion — Mac/Linux launcher
cd "$(dirname "$0")" || exit 1
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
exec "$PY" run_companion.py
