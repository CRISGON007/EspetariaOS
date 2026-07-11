#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

VERSION="${1:-v0.4.9}"
COMMIT_MESSAGE="${2:-release: publica EspetariaOS ${VERSION}}"
RELEASE_BRANCH="release/${VERSION}"

fail() {
  echo "ERRO: $*" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "Git não está instalado."
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Esta pasta não é um repositório Git."
git remote get-url origin >/dev/null 2>&1 || fail "O remoto origin não está configurado."

if [[ ! -x ".venv/bin/python" ]]; then
  fail "Ambiente virtual ausente. Execute ./install.sh."
fi

echo "=========================================="
echo " Finalização da versão ${VERSION}"
echo "=========================================="
echo
echo "Remoto: $(git remote get-url origin)"
echo "Branch atual: $(git branch --show-current)"
echo

echo "Executando testes automatizados..."
./testar.sh

echo
echo "Estado atual do repositório:"
git status --short

if [[ -z "$(git status --porcelain)" ]]; then
  fail "Não existem alterações para registrar."
fi

echo
read -r -p "Os testes manuais também foram aprovados? [s/N] " MANUAL_OK
[[ "${MANUAL_OK,,}" == "s" ]] || fail "Processo cancelado. Nenhuma alteração foi enviada."

CURRENT_BRANCH="$(git branch --show-current)"

if [[ "$CURRENT_BRANCH" == "main" ]]; then
  if git show-ref --verify --quiet "refs/heads/${RELEASE_BRANCH}"; then
    git switch "$RELEASE_BRANCH"
  else
    git switch -c "$RELEASE_BRANCH"
  fi
elif [[ "$CURRENT_BRANCH" != "$RELEASE_BRANCH" ]]; then
  echo "Você está na branch ${CURRENT_BRANCH}."
  read -r -p "Continuar nela em vez de ${RELEASE_BRANCH}? [s/N] " KEEP_BRANCH
  [[ "${KEEP_BRANCH,,}" == "s" ]] || fail "Mude para a branch desejada e execute novamente."
  RELEASE_BRANCH="$CURRENT_BRANCH"
fi

git add .

echo
echo "Arquivos preparados:"
git status --short

read -r -p "Criar o commit '${COMMIT_MESSAGE}'? [s/N] " COMMIT_OK
[[ "${COMMIT_OK,,}" == "s" ]] || fail "Processo cancelado antes do commit."

git commit -m "$COMMIT_MESSAGE"
git push -u origin "$RELEASE_BRANCH"

echo
echo "Branch enviada: ${RELEASE_BRANCH}"
read -r -p "Mesclar agora na main e criar a tag ${VERSION}? [s/N] " MERGE_OK

if [[ "${MERGE_OK,,}" != "s" ]]; then
  echo "Processo concluído até a branch de release."
  echo "Após revisar no GitHub, faça o merge manualmente ou execute novamente."
  exit 0
fi

git switch main
git pull --ff-only origin main
git merge --no-ff "$RELEASE_BRANCH" -m "merge: integra ${VERSION}"
git push origin main

if git rev-parse "$VERSION" >/dev/null 2>&1; then
  echo "A tag ${VERSION} já existe; ela não será recriada."
else
  git tag -a "$VERSION" -m "EspetariaOS ${VERSION}"
  git push origin "$VERSION"
fi

echo
echo "=========================================="
echo " Versão ${VERSION} publicada com sucesso"
echo "=========================================="
echo "Branch: main"
echo "Tag: ${VERSION}"
echo
git status
