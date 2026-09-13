#!/bin/bash
cd "$(dirname "$0")"
if [ -x ../../../../.venv/bin/python ]; then
  exec ../../../../.venv/bin/python launch.py stop
else
  exec python3 launch.py stop
fi
