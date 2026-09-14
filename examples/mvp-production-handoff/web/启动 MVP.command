#!/bin/bash
cd "$(dirname "$0")"
if [ -x ../../../../.venv/bin/python ]; then
  exec ../../../../.venv/bin/python launch.py start
else
  exec python3 launch.py start
fi
