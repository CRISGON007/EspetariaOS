#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

echo "=========================================="
echo " EspetariaOS - Preparação do ambiente"
echo "=========================================="

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERRO: Python 3 não está instalado."
  echo "Instale com: sudo apt update && sudo apt install -y python3"
  exit 1
fi

if ! python3 -c "import venv" >/dev/null 2>&1; then
  echo "O módulo venv não está disponível."
  echo "Execute: sudo apt update && sudo apt install -y python3-venv"
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  echo "Criando o ambiente virtual .venv..."
  python3 -m venv .venv
else
  echo "Ambiente virtual existente encontrado."
fi

source .venv/bin/activate

echo "Atualizando ferramentas do Python..."
python -m pip install --upgrade pip setuptools wheel

echo "Instalando dependências do projeto..."
python -m pip install -r requirements.txt

echo "Verificando suporte ao WebSocket..."
python - <<'PY'
import fastapi
import uvicorn
import websockets
import wsproto
import psutil
print("FastAPI ........ OK")
print("Uvicorn ........ OK")
print("WebSockets ..... OK")
print("wsproto ........ OK")
print("psutil ......... OK")
PY

mkdir -p data backups logs

echo
echo "=========================================="
echo " Ambiente preparado com sucesso"
echo "=========================================="
echo "Produção: ./start.sh"
echo "Desenvolvimento/testes: ./dev.sh"
