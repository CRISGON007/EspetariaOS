#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
echo "=========================================="
echo " EspetariaOS v1.0.1 - Diagnóstico"
echo "=========================================="
ERRORS=0
ok(){ echo "[OK] $1"; }
fail(){ echo "[ERRO] $1"; ERRORS=$((ERRORS+1)); }
command -v python3 >/dev/null 2>&1 && ok "Python 3: $(python3 --version)" || fail "Python 3 ausente."
[[ -x .venv/bin/python ]] && ok "Ambiente virtual encontrado." || fail "Ambiente virtual ausente."
for d in data backups logs; do mkdir -p "$d"; [[ -w "$d" ]] && ok "$d/ gravável" || fail "$d/ sem permissão"; done
if [[ -x .venv/bin/python ]]; then
  PYTHONPATH="$PROJECT_DIR" ESPETARIA_ENV=production ESPETARIA_DEMO=false     .venv/bin/python -c "from app.main import app; print(app.title)" >/dev/null     && ok "Aplicação importada." || fail "Falha ao importar aplicação."
  if PYTHONPATH="$PROJECT_DIR" .venv/bin/python - <<'PY'
from app.config import settings
from app.system_service import database_integrity
r=database_integrity(settings.database_path)
print(r["message"])
raise SystemExit(0 if r["ok"] else 1)
PY
  then ok "Integridade do banco confirmada."; else fail "Banco ausente ou inválido."; fi
fi
if command -v ss >/dev/null 2>&1 && ss -ltn | grep -q ':8080 '; then
  echo "[AVISO] Porta 8080 em uso."
else
  ok "Porta 8080 disponível."
fi
[[ "$ERRORS" -eq 0 ]] && { echo "Diagnóstico concluído sem erros."; exit 0; }
echo "Diagnóstico concluído com $ERRORS erro(s)."; exit 1
