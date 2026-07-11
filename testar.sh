#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Ambiente virtual não encontrado."
  echo "Execute primeiro: ./install.sh"
  exit 1
fi

export PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "Diretório do projeto: $PROJECT_DIR"
echo "PYTHONPATH: $PYTHONPATH"

echo "1/3 - Validando sintaxe Python..."
.venv/bin/python -m compileall -q app tests run.py

echo "2/3 - Executando teste do banco..."
.venv/bin/python tests/test_database.py

echo "3/3 - Verificando importação da aplicação..."
ESPETARIA_ENV=development \
ESPETARIA_DEMO=true \
ESPETARIA_DB=data/teste_importacao.db \
.venv/bin/python -c \
"from app.main import app; print('Aplicação importada:', app.title)"

rm -f \
  data/teste_importacao.db \
  data/teste_importacao.db-shm \
  data/teste_importacao.db-wal

echo
echo "Todos os testes automatizados foram concluídos com sucesso."
