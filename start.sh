#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Ambiente virtual não encontrado. Execute primeiro: ./install.sh"
  exit 1
fi

export ESPETARIA_ENV=production
export ESPETARIA_DEMO=false

exec .venv/bin/python run.py
