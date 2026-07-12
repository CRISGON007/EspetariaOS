#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
[[ -x .venv/bin/python ]] || { echo "ERRO: execute ./install.sh."; exit 1; }
mkdir -p backups data logs
echo "1/4 - Backup pré-atualização..."
PYTHONPATH="$PROJECT_DIR" .venv/bin/python - <<'PY'
from app.config import settings
from app.system_service import create_backup
from pathlib import Path
if Path(settings.database_path).exists():
    print("Backup:", create_backup(settings.database_path, settings.backups_dir))
else:
    print("Banco ainda não existe.")
PY
echo "2/4 - Dependências..."
.venv/bin/python -m pip install -r requirements.txt
echo "3/4 - Testes..."
./testar.sh
echo "4/4 - Diagnóstico..."
./diagnostico.sh
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^espetariaos.service'; then
  read -r -p "Reiniciar serviço agora? [s/N] " R
  [[ "${R,,}" == "s" ]] && sudo systemctl restart espetariaos
else
  echo "Inicie com ./start.sh"
fi
echo "Atualização concluída."
