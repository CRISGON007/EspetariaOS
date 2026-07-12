#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then echo "Uso: ./publicar_git.sh v1.0.1"; exit 1; fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "ERRO: esta pasta não é um repositório Git."; exit 1; }
git remote get-url origin >/dev/null 2>&1 || { echo "ERRO: remoto origin não configurado."; exit 1; }
BRANCH="$(git branch --show-current)"
[[ -n "$BRANCH" ]] || { echo "ERRO: detached HEAD."; exit 1; }
git rev-parse "$VERSION" >/dev/null 2>&1 && { echo "ERRO: a tag $VERSION já existe."; exit 1; }
echo "Branch: $BRANCH"
./testar.sh
git status --short
[[ -n "$(git status --porcelain)" ]] || { echo "ERRO: não existem alterações para publicar."; exit 1; }
read -r -p "Publicar $VERSION no GitHub? [s/N] " CONFIRM
[[ "${CONFIRM,,}" == "s" ]] || exit 0
git add .
git commit -m "feat: publica EspetariaOS $VERSION"
git push origin "$BRANCH"
git tag -a "$VERSION" -m "EspetariaOS $VERSION"
git push origin "$VERSION"
echo "Versão publicada: $VERSION"
