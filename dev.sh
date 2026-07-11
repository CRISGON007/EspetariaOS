#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Ambiente virtual não encontrado. Execute primeiro: ./install.sh"
  exit 1
fi

export ESPETARIA_ENV=development
export ESPETARIA_DEMO=true
export ESPETARIA_DB="${ESPETARIA_DB:-data/teste_v0.6.1.db}"

echo "Banco de testes: $ESPETARIA_DB"
exec .venv/bin/python run.py
